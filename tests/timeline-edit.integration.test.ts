import fs from "node:fs/promises";
import path from "node:path";
import {describe,expect,it} from "vitest";
import {AppDatabase} from "../src/main/db";
import {CompositionManager} from "../src/main/composition";
import {ProductEvidence} from "../src/main/product-evidence";
import {runTool} from "../src/main/tools";
import {CompositionSpec} from "../src/shared/contracts";

async function wait(db:AppDatabase,id:string){for(let index=0;index<150;index++){const job=db.getComposition(id);if(job?.status==="completed")return job;if(job?.status==="failed")throw new Error(JSON.stringify(job.error));await new Promise(resolve=>setTimeout(resolve,75));}throw new Error("timeline render timeout");}

describe("timeline edit render",()=>{
  it("validates ordered edit paths and time ranges",()=>{const base={videoPath:"a.mp4",audioPath:"a.m4a",destinationDir:"out"};expect(()=>CompositionSpec.parse({...base,videoEdits:[{path:"wrong.mp4"}]})).toThrow("match");expect(()=>CompositionSpec.parse({...base,videoEdits:[{path:"a.mp4",trimStart:2,trimEnd:1}]})).toThrow("after");expect(()=>CompositionSpec.parse({...base,logos:[{path:"logo.png",timelineStart:2,timelineEnd:1}]})).toThrow("after");});
  it("allows split segments to reference the same source",()=>{const parsed=CompositionSpec.parse({videoPath:"a.mp4",additionalVideoPaths:["a.mp4"],videoEdits:[{path:"a.mp4",trimStart:0,trimEnd:1},{path:"a.mp4",trimStart:1,trimEnd:2}],audioPath:"a.m4a",destinationDir:"out"});expect(parsed.videoEdits).toHaveLength(2);});
  it("exports the edited duration instead of the source duration",async()=>{const root=await fs.mkdtemp(path.join(process.env.TEMP??process.cwd(),"svp-timeline-"));const video=path.join(root,"video.mp4"),audio=path.join(root,"audio.m4a");expect((await runTool("ffmpeg",["-y","-f","lavfi","-i","testsrc2=s=320x180:r=30:d=4","-c:v","libx264","-pix_fmt","yuv420p",video])).code).toBe(0);expect((await runTool("ffmpeg",["-y","-f","lavfi","-i","sine=frequency=440:duration=4","-c:a","aac",audio])).code).toBe(0);const db=new AppDatabase(path.join(root,"data"));const manager=new CompositionManager(db,new ProductEvidence(db));const created=manager.create({videoPath:video,videoEdits:[{path:video,trimStart:1,trimEnd:3,speed:2}],audioPath:audio,audioVolume:.5,destinationDir:root,outputName:"edited"});const done=await wait(db,created.id);expect(done.finalArtifact?.durationSeconds).toBeGreaterThan(.8);expect(done.finalArtifact?.durationSeconds).toBeLessThan(1.3);db.close();await fs.rm(root,{recursive:true,force:true});},60000);
});
