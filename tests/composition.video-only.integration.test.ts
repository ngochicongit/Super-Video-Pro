import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import {describe,expect,it} from "vitest";
import {AppDatabase} from "../src/main/db";
import {CompositionManager} from "../src/main/composition";
import {ProductEvidence} from "../src/main/product-evidence";
import {runTool} from "../src/main/tools";

async function waitForCompletion(db:AppDatabase,id:string){
  for(let attempt=0;attempt<120;attempt++){
    const job=db.getComposition(id);
    if(job?.status==="completed"||job?.status==="failed")return job;
    await new Promise(resolve=>setTimeout(resolve,50));
  }
  throw new Error("Timed out waiting for video-only composition");
}

describe("video-only logo composition",()=>{
  it("exports a valid video with a logo and no audio track",async()=>{
    const root=await fs.mkdtemp(path.join(os.tmpdir(),"svp-video-only-"));
    const video=path.join(root,"video.mp4"),logo=path.join(root,"logo.png");
    expect((await runTool("ffmpeg",["-y","-f","lavfi","-i","color=c=blue:s=320x180:r=30:d=1","-c:v","libx264","-pix_fmt","yuv420p",video])).code).toBe(0);
    expect((await runTool("ffmpeg",["-y","-f","lavfi","-i","color=c=red:s=48x32:d=1","-frames:v","1",logo])).code).toBe(0);
    const db=new AppDatabase(path.join(root,"data"));
    const manager=new CompositionManager(db,new ProductEvidence(db));
    const created=manager.create({videoPath:video,logos:[{path:logo}],destinationDir:root,outputName:"silent-logo"});
    const done=await waitForCompletion(db,created.id);
    expect(done.status).toBe("completed");
    expect(done.outputPath).toBe(path.join(root,"silent-logo.mp4"));
    expect((await fs.stat(done.outputPath!)).size).toBeGreaterThan(0);
    db.close();
    await fs.rm(root,{recursive:true,force:true});
  },60000);
});
