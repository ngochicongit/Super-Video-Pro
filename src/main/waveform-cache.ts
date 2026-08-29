import {createHash} from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import {runTool} from "./tools.js";

export function waveformCacheName(file:string,size:number,mtimeMs:number){
  return `${createHash("sha256").update(`${path.resolve(file)}\0${size}\0${mtimeMs}`).digest("hex")}.png`;
}

export async function ensureWaveform(file:string,cacheDir:string){
  const stat=await fs.stat(file);
  if(!stat.isFile())throw new Error("Waveform input is not a file");
  await fs.mkdir(cacheDir,{recursive:true});
  const output=path.join(cacheDir,waveformCacheName(file,stat.size,stat.mtimeMs));
  try{await fs.access(output);return output;}catch{}
  const temporary=`${output}.${process.pid}.${Date.now()}.tmp.png`;
  try{
    const result=await runTool("ffmpeg",["-y","-v","error","-i",file,"-filter_complex","aformat=channel_layouts=mono,showwavespic=s=1600x120:colors=5ee6d0","-frames:v","1",temporary]);
    if(result.code!==0)throw Object.assign(new Error(result.stderr.trim()||"FFmpeg could not generate waveform"),{code:"WAVEFORM_FAILED"});
    await fs.rename(temporary,output);
    return output;
  }finally{await fs.rm(temporary,{force:true}).catch(()=>{});}
}
