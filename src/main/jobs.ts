import { EventEmitter } from "node:events";
import os from "node:os"; import path from "node:path";
import { nanoid } from "nanoid";
import { AppSettings, DownloadJob, type DownloadJob as Job } from "../shared/contracts.js";
import { FinalArtifact, MediaArtifact } from "../shared/contracts.js";
import { normalizeError } from "../shared/errors.js";
import { AppDatabase } from "./db.js";
import { ExtractionPipeline } from "./extraction.js";
import { downloadExternal, downloadHttp } from "./downloader.js";
import { validateFinal } from "./validation.js";
import { ensureStorage } from "./storage.js";

export class JobManager extends EventEmitter {
  private running = new Map<string, AbortController>(); private ticking = false;
  constructor(private db: AppDatabase, private extraction = new ExtractionPipeline()) { super();this.applyRetention(this.settings());this.recover(); }
  settings(): AppSettings { const defaults={downloadDir:path.join(os.homedir(),"Downloads","Super Video Pro"),concurrency:2,perDomainConcurrency:1,cookiesFromBrowser:"none" as const,collectProductEvidence:false,historyRetentionDays:90,logRetentionDays:30,backupRetentionCount:3};const stored=this.db.getSetting<Record<string,unknown>>("app",{});const parsed=AppSettings.safeParse({...defaults,...stored});if(parsed.success)return parsed.data;this.db.quarantineSetting("app",stored,parsed.error);return AppSettings.parse(defaults); }
  updateSettings(patch: Partial<AppSettings>) { const next = AppSettings.parse({ ...this.settings(), ...patch });this.db.setSetting("app", next);this.applyRetention(next);void this.tick();return next; }
  list(limit=100) { return this.db.listJobs(limit); }
  async inspect(sourceUrl:string){const settings=this.settings();return this.extraction.extract(sourceUrl,new AbortController().signal,{cookiesFromBrowser:settings.cookiesFromBrowser,allowThirdPartyXFallback:settings.allowThirdPartyXFallback})}
  create(input: {sourceUrl:string; destinationDir?:string; priority:number;selectedVariantId?:string;resource?:Job["resource"]}) {
    const now = new Date().toISOString(); const job = DownloadJob.parse({ id:nanoid(), createdAt:now, updatedAt:now, sourceUrl:input.sourceUrl, destinationDir:input.destinationDir ?? this.settings().downloadDir, status:"queued", priority:input.priority,selectedVariantId:input.selectedVariantId,resource:input.resource });
    this.save(job); void this.tick(); return job;
  }
  command(id: string, action: "pause"|"resume"|"cancel"|"retry") {
    const job=this.require(id); const controller=this.running.get(id);
    if (action==="pause") { if (!["running","retrying"].includes(job.status)) throw new Error("Job is not active"); controller?.abort(); return this.save({...job,status:"paused"}); }
    if (action==="cancel") { if (["completed","cancelled"].includes(job.status)) return job; controller?.abort(); return this.save({...job,status:"cancelled"}); }
    if (action==="resume") { if (job.status!=="paused") throw new Error("Job is not paused"); const next=this.save({...job,status:"queued",error:undefined}); void this.tick(); return next; }
    if (job.status!=="failed") throw new Error("Job is not failed"); const next=this.save({...job,status:"queued",error:undefined}); void this.tick(); return next;
  }
  remove(id:string){const job=this.require(id);if(!["completed","cancelled"].includes(job.status))throw new Error("Only completed or cancelled jobs can be removed");return {removed:this.db.deleteJob(id)};}
  clearTerminal(statuses:("completed"|"cancelled")[]){return {removed:this.db.deleteJobsByStatus(statuses)};}
  private require(id:string){ const job=this.db.getJob(id); if(!job) throw new Error("Job not found"); return job; }
  private save(job:Job){ const parsed=DownloadJob.parse({...job,updatedAt:new Date().toISOString()}); this.db.saveJob(parsed); this.emit("changed",parsed); return parsed; }
  private recover(){ for(const job of this.db.listJobs(500)) if(["running","retrying","processing","validating"].includes(job.status)) this.save({...job,status:"queued",error:undefined}); queueMicrotask(()=>void this.tick()); }
  private applyRetention(settings:AppSettings){const cutoff=new Date(Date.now()-settings.historyRetentionDays*86_400_000).toISOString();this.db.deleteTerminalBefore(cutoff);this.db.pruneBackups(settings.backupRetentionCount);}
  private async tick(){ if(this.ticking)return; this.ticking=true; try { while(this.running.size<this.settings().concurrency){ const perDomain=new Map<string,number>();for(const id of this.running.keys()){const active=this.db.getJob(id);if(active){const domain=this.domain(active.sourceUrl);perDomain.set(domain,(perDomain.get(domain)??0)+1);}}const job=this.db.listJobs(500).filter(j=>j.status==="queued"&&(perDomain.get(this.domain(j.sourceUrl))??0)<this.settings().perDomainConcurrency).sort((a,b)=>b.priority-a.priority||a.createdAt.localeCompare(b.createdAt))[0]; if(!job)break; const controller=new AbortController(); this.running.set(job.id,controller); void this.execute(job,controller).finally(()=>{this.running.delete(job.id);void this.tick();}); } } finally { this.ticking=false; } }
  private domain(sourceUrl:string){try{return new URL(sourceUrl).hostname.toLowerCase()}catch{return "invalid"}}
  private async execute(job:Job, controller:AbortController){
    let active=this.save({...job,status:"running",attempts:job.attempts+1});
    try {const prepared=await this.prepareDownload(active,controller);active=prepared.active;await this.completeDownload(active,prepared.result);}
    catch(error){this.handleExecutionError(active,error);}
  }
  private async prepareDownload(active:Job,controller:AbortController){
    if(active.downloadedPath)return{active,result:{path:active.downloadedPath,size:active.bytesDownloaded}};
    const settings=this.settings();let resource=active.resource??await this.extraction.extract(active.sourceUrl,controller.signal,{cookiesFromBrowser:settings.cookiesFromBrowser,allowThirdPartyXFallback:settings.allowThirdPartyXFallback});
    if(active.selectedVariantId){const selected=resource.variants.find(v=>v.id===active.selectedVariantId);if(!selected)throw Object.assign(new Error("Selected quality is no longer available"),{code:"INVALID_INPUT"});resource={...resource,variants:[selected,...resource.variants.filter(v=>v.id!==selected.id)]};}
    active=this.save({...active,resource});await ensureStorage(active.destinationDir);
    const report=(progress:{bytesDownloaded:number;totalBytes:number|null})=>{const current=this.db.getJob(active.id);if(current?.status==="running")active=this.save({...current,bytesDownloaded:progress.bytesDownloaded,totalBytes:progress.totalBytes,progress:progress.totalBytes?progress.bytesDownloaded/progress.totalBytes:0});};
    const protocol=resource.variants[0]?.protocol;const result=protocol==="http"?await downloadHttp(resource,active.destinationDir,controller.signal,report):await downloadExternal(resource,active.destinationDir,controller.signal,report,{cookiesFromBrowser:this.settings().cookiesFromBrowser});
    return{active:this.save({...active,status:"processing",downloadedPath:result.path,bytesDownloaded:result.size}),result};
  }
  private async completeDownload(active:Job,result:{path:string;size:number}){
    active=this.save({...active,status:"validating"});const validation=await validateFinal(result.path);
    const media=MediaArtifact.parse({id:nanoid(),jobId:active.id,kind:validation.valid?"downloaded":"invalid",path:result.path,size:validation.size,createdAt:new Date().toISOString(),validation});this.db.saveArtifact(media);
    if(!validation.valid)throw Object.assign(new Error(`Final validation failed: ${validation.reasons.join("; ")}`),{code:"FINAL_INVALID"});
    const final=FinalArtifact.parse({id:nanoid(),jobId:active.id,sourceArtifactIds:[media.id],path:result.path,displayName:result.path.split(/[\\/]/).pop()||"download",size:validation.size,createdAt:new Date().toISOString(),container:validation.container,durationSeconds:validation.durationSeconds});this.db.saveArtifact({...final,kind:"final"});
    this.save({...active,status:"completed",progress:1,bytesDownloaded:validation.size,totalBytes:validation.size});
  }
  private handleExecutionError(active:Job,error:unknown){
    const current=this.db.getJob(active.id);if(!current||["paused","cancelled"].includes(current.status))return;
    const normalized=normalizeError(error,"download");const retry=normalized.retryable&&current.attempts<current.maxAttempts;this.save({...current,status:retry?"retrying":"failed",error:normalized});
    if(retry)setTimeout(()=>{const latest=this.db.getJob(current.id);if(latest?.status==="retrying"){this.save({...latest,status:"queued"});void this.tick();}},Math.min(30000,1000*2**current.attempts));
  }
}
