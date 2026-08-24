import { afterEach, describe, expect, it } from "vitest";
import http from "node:http";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { downloadExternal } from "../src/main/downloader";
import { runTool } from "../src/main/tools";
import { validateFinal } from "../src/main/validation";

const servers:http.Server[]=[];
afterEach(()=>Promise.all(servers.map(server=>new Promise<void>(resolve=>server.close(()=>resolve())))));
async function serve(dir:string){const server=http.createServer(async(req,res)=>{try{const name=decodeURIComponent(new URL(req.url??"/","http://fixture").pathname.slice(1));const file=path.join(dir,name);const data=await fs.readFile(file);const type=name.endsWith(".m3u8")?"application/vnd.apple.mpegurl":name.endsWith(".mpd")?"application/dash+xml":name.endsWith(".m4s")?"video/iso.segment":"video/mp2t";res.writeHead(200,{"content-type":type,"content-length":data.length});res.end(data)}catch{res.writeHead(404);res.end()}});servers.push(server);await new Promise<void>(resolve=>server.listen(0,"127.0.0.1",()=>resolve()));return (server.address() as {port:number}).port;}
async function fixtureRoot(prefix:string){return fs.mkdtemp(path.join(os.tmpdir(),prefix));}

describe("stream engines with local fixture server",()=>{
  it("downloads and validates HLS",async()=>{const root=await fixtureRoot("svp-hls-");const source=path.join(root,"source");const output=path.join(root,"output");await fs.mkdir(source);const generated=await runTool("ffmpeg",["-y","-f","lavfi","-i","testsrc=size=64x64:rate=10","-t","0.6","-an","-c:v","libx264","-pix_fmt","yuv420p","-f","hls","-hls_time","0.2",path.join(source,"playlist.m3u8")]);expect(generated.code).toBe(0);const port=await serve(source);const url=`http://127.0.0.1:${port}/playlist.m3u8`;const resource={version:1 as const,sourceUrl:url,title:"hls-fixture",extractor:"fixture",protection:"none" as const,variants:[{id:"hls",url,protocol:"hls" as const}],subtitles:[],metadata:{}};const result=await downloadExternal(resource,output,new AbortController().signal,()=>{});expect((await validateFinal(result.path)).valid).toBe(true);await fs.rm(root,{recursive:true,force:true})},15000);
  it("downloads and validates DASH",async()=>{const root=await fixtureRoot("svp-dash-");const source=path.join(root,"source");const output=path.join(root,"output");await fs.mkdir(source);const generated=await runTool("ffmpeg",["-y","-f","lavfi","-i","testsrc=size=64x64:rate=10","-t","0.6","-an","-c:v","libx264","-pix_fmt","yuv420p","-f","dash","manifest.mpd"],{cwd:source});expect(generated.code).toBe(0);const port=await serve(source);const url=`http://127.0.0.1:${port}/manifest.mpd`;const resource={version:1 as const,sourceUrl:url,title:"dash-fixture",extractor:"fixture",protection:"none" as const,variants:[{id:"dash",url,protocol:"dash" as const}],subtitles:[],metadata:{}};const result=await downloadExternal(resource,output,new AbortController().signal,()=>{});expect((await validateFinal(result.path)).valid).toBe(true);await fs.rm(root,{recursive:true,force:true})},15000);
});
