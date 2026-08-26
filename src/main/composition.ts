import {EventEmitter} from "node:events";
import fs from "node:fs/promises";
import path from "node:path";
import {nanoid} from "nanoid";
import {CompositionJob,CompositionSpec,FinalArtifact,type CompositionJob as Job,type CompositionSpec as Spec} from "../shared/contracts.js";
import {normalizeError} from "../shared/errors.js";
import type {AppDatabase} from "./db.js";
import type {ProductEvidence} from "./product-evidence.js";
import {runTool} from "./tools.js";
import {validateFinal} from "./validation.js";
import {compositionArgs} from "./composition-ffmpeg.js";

function safeName(value:string|undefined){const raw=value?.trim()||`composition-${new Date().toISOString().replace(/[:.]/g,"-")}`;const base=raw.replace(/\.mp4$/i,"").replace(/[<>:"/\\|?*\u0000-\u001f]/g,"-").replace(/\.+$/g,"").slice(0,110);return `${base||"composition"}.mp4`;}
export async function inspectCompositionInput(file:string){const result=await runTool("ffprobe",["-v","error","-show_entries","format=duration:stream=codec_type,width,height","-of","json",file]);if(result.code!==0)throw Object.assign(new Error("FFprobe could not inspect a composition input"),{code:"COMPOSITION_INVALID_MEDIA"});const parsed=JSON.parse(result.stdout) as {format?:{duration?:string};streams?:Array<{codec_type?:string;width?:number;height?:number}>};const video=parsed.streams?.find(item=>item.codec_type==="video");return{duration:Number(parsed.format?.duration)||0,kinds:new Set((parsed.streams??[]).map(item=>item.codec_type)),width:video?.width??0,height:video?.height??0};}
export function multiVideoArgs(videoPaths:string[],audioPath:string|undefined,temp:string,width:number,height:number){return compositionArgs({videoPaths,audioPath,tempPath:temp,width,height});}

export class CompositionManager extends EventEmitter{
  private running=new Map<string,AbortController>();
  constructor(private db:AppDatabase,private evidence:ProductEvidence,private collectEvidence:()=>boolean=()=>false,private historyRetentionDays:()=>number=()=>90){super();for(const job of db.listCompositions())if(["queued","processing","validating"].includes(job.status))this.save({...job,status:"failed",error:{code:"INTERRUPTED",message:"Composition was interrupted by application shutdown"}});}
  list(){const cutoff=new Date(Date.now()-this.historyRetentionDays()*86400000).toISOString();this.db.deleteTerminalCompositionsBefore(cutoff);return this.db.listCompositions();}
  create(raw:Spec){const spec=CompositionSpec.parse(raw);const now=new Date().toISOString();const job=CompositionJob.parse({id:nanoid(),createdAt:now,updatedAt:now,status:"queued",spec});if(this.collectEvidence()){this.evidence.record("composition.intent");if(spec.additionalVideoPaths?.length)this.evidence.record("composition.multi_input_intent");}this.save(job);void this.execute(job);return job;}
  command(id:string,action:"cancel"|"retry"){const job=this.require(id);if(action==="cancel"){if(["completed","cancelled"].includes(job.status))return job;this.running.get(id)?.abort();return this.save({...job,status:"cancelled"});}if(job.status!=="failed")throw new Error("Only failed compositions can be retried");const next=this.save({...job,status:"queued",error:undefined,progress:0});void this.execute(next);return next;}
  remove(id:string){const job=this.require(id);if(!["completed","failed","cancelled"].includes(job.status))throw new Error("Only terminal compositions can be removed from history");return this.db.deleteComposition(id);}
  private require(id:string){const job=this.db.getComposition(id);if(!job)throw new Error("Composition job not found");return job;}
  private save(job:Job){const parsed=CompositionJob.parse({...job,updatedAt:new Date().toISOString()});this.db.saveComposition(parsed);this.emit("changed",parsed);return parsed;}
  private async execute(initial:Job){
    const controller=new AbortController();this.running.set(initial.id,controller);let job=this.save({...initial,status:"processing",progress:.05});let temp="";
    try{
      const videoPaths=[job.spec.videoPath,...(job.spec.additionalVideoPaths??[])];const logos=job.spec.logos??[];
      await Promise.all([...videoPaths,...(job.spec.audioPath?[job.spec.audioPath]:[]),...logos.map(logo=>logo.path)].map(file=>fs.access(file)));
      const videos=await Promise.all(videoPaths.map(inspectCompositionInput));const audio=job.spec.audioPath?await inspectCompositionInput(job.spec.audioPath):undefined;
      if(videos.some(video=>!video.kinds.has("video")))throw Object.assign(new Error("A selected video file has no video stream"),{code:"COMPOSITION_VIDEO_STREAM"});
      if(audio&&!audio.kinds.has("audio"))throw Object.assign(new Error("The selected audio file has no audio stream"),{code:"COMPOSITION_AUDIO_STREAM"});
      const videoDuration=job.spec.videoEdits?.reduce((total,edit,index)=>total+((edit.trimEnd??videos[index]?.duration??0)-edit.trimStart)/edit.speed,0)??videos.reduce((total,video)=>total+video.duration,0);
      if(videoDuration&&audio?.duration&&(job.spec.videoEdits?audio.duration<videoDuration-.5:Math.abs(videoDuration-audio.duration)>.5))throw Object.assign(new Error(job.spec.videoEdits?"Audio is shorter than the edited video timeline":"Combined video and audio durations differ by more than 0.5 seconds"),{code:"COMPOSITION_DURATION"});
      await fs.mkdir(job.spec.destinationDir,{recursive:true});const output=path.join(job.spec.destinationDir,safeName(job.spec.outputName));
      try{await fs.access(output);throw Object.assign(new Error("The composition output already exists; choose another name"),{code:"COMPOSITION_OUTPUT_EXISTS"});}catch(error){if((error as NodeJS.ErrnoException).code!=="ENOENT")throw error;}
      temp=`${output}.processing`;await fs.rm(temp,{force:true});const first=videos[0]!;
      const args=compositionArgs({videoPaths,videoEdits:job.spec.videoEdits,audioPath:job.spec.audioPath,audioVolume:job.spec.audioVolume,logos,tempPath:temp,width:first.width||1280,height:first.height||720});
      const result=await runTool("ffmpeg",args,{signal:controller.signal});if(result.code!==0)throw Object.assign(new Error(result.stderr.trim()||"FFmpeg composition failed"),{code:"COMPOSITION_PROCESSING"});
      job=this.save({...job,status:"validating",progress:.9});const validation=await validateFinal(temp);if(!validation.valid)throw Object.assign(new Error(`Composition validation failed: ${validation.reasons.join("; ")}`),{code:"FINAL_INVALID"});
      await fs.rename(temp,output);const final=FinalArtifact.parse({id:nanoid(),jobId:job.id,sourceArtifactIds:[...videoPaths.map(file=>`local:${file}`),...(job.spec.audioPath?[`local:${job.spec.audioPath}`]:[]),...logos.map(logo=>`local:${logo.path}`)],path:output,displayName:path.basename(output),size:validation.size,createdAt:new Date().toISOString(),container:validation.container,durationSeconds:validation.durationSeconds});if(this.collectEvidence())this.evidence.record("composition.export_completed");this.save({...job,status:"completed",progress:1,outputPath:output,finalArtifact:final});
    }catch(error){if(temp)await fs.rm(temp,{force:true}).catch(()=>undefined);const current=this.db.getComposition(initial.id);if(current?.status!=="cancelled")this.save({...current!,status:"failed",error:normalizeError(error,"process")});}
    finally{this.running.delete(initial.id);}
  }
}
