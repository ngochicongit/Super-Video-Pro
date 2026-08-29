import fs from "node:fs/promises";
import path from "node:path";
import {describe,expect,it} from "vitest";
import {ensureWaveform,waveformCacheName} from "../src/main/waveform-cache";
import {runTool} from "../src/main/tools";

describe("audio waveform cache",()=>{
  it("fingerprints file identity and metadata",()=>{expect(waveformCacheName("audio.m4a",10,20)).toBe(waveformCacheName("audio.m4a",10,20));expect(waveformCacheName("audio.m4a",10,20)).not.toBe(waveformCacheName("audio.m4a",11,20));});
  it("renders once and reuses the cached PNG",async()=>{const root=await fs.mkdtemp(path.join(process.env.TEMP??process.cwd(),"svp-waveform-"));try{const audio=path.join(root,"audio.m4a"),cache=path.join(root,"cache");expect((await runTool("ffmpeg",["-y","-v","error","-f","lavfi","-i","sine=frequency=440:duration=0.4","-c:a","aac",audio])).code).toBe(0);const first=await ensureWaveform(audio,cache),before=await fs.stat(first);await new Promise(resolve=>setTimeout(resolve,20));const second=await ensureWaveform(audio,cache),after=await fs.stat(second);expect(second).toBe(first);expect(after.mtimeMs).toBe(before.mtimeMs);expect(after.size).toBeGreaterThan(100);}finally{await fs.rm(root,{recursive:true,force:true});}},30000);
});
