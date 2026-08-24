import fs from "node:fs/promises";
import path from "node:path";

function mediaIdFromUrl(sourceUrl:string){
  try{
    const url=new URL(sourceUrl);
    return url.hostname==="youtu.be"?url.pathname.slice(1):url.searchParams.get("v")??url.pathname.match(/\/status\/(\d+)/)?.[1];
  }catch{return undefined;}
}

export async function resolveExternalOutput(destinationDir:string,candidates:string[],sourceUrl:string,startedAt:number){
  for(const candidate of [...candidates].reverse()){
    if(!path.isAbsolute(candidate))continue;
    try{const stat=await fs.stat(candidate);if(stat.isFile())return candidate;}catch{}
  }
  const mediaId=mediaIdFromUrl(sourceUrl);
  const files=await Promise.all((await fs.readdir(destinationDir)).map(async name=>{
    const full=path.join(destinationDir,name);
    try{
      const stat=await fs.stat(full);
      return stat.isFile()&&!/\.(part|ytdl)$/i.test(name)&&stat.mtimeMs>=startedAt-2000&&(!mediaId||name.includes(`[${mediaId}]`))?{full,mtime:stat.mtimeMs}:null;
    }catch{return null;}
  }));
  const newest=files.filter((item):item is {full:string;mtime:number}=>Boolean(item)).sort((a,b)=>b.mtime-a.mtime)[0];
  if(!newest)throw new Error("yt-dlp completed but the final output path could not be resolved");
  return newest.full;
}
