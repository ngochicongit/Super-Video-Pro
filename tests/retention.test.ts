import {afterEach,describe,expect,it} from "vitest";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import {AppDatabase} from "../src/main/db";
import {Diagnostics} from "../src/main/diagnostics";

const roots:string[]=[];afterEach(async()=>{await Promise.all(roots.splice(0).map(root=>fs.rm(root,{recursive:true,force:true})));});
async function root(prefix:string){const value=await fs.mkdtemp(path.join(os.tmpdir(),prefix));roots.push(value);return value;}

describe("retention controls",()=>{
  it("removes only terminal jobs older than the cutoff",async()=>{const dir=await root("svp-retention-db-");const db=new AppDatabase(dir);const base={destinationDir:dir,priority:50,attempts:0,maxAttempts:3,progress:1,bytesDownloaded:1,totalBytes:1};db.saveJob({...base,id:"old-complete",createdAt:"2020-01-01T00:00:00.000Z",updatedAt:"2020-01-01T00:00:00.000Z",sourceUrl:"https://example.com/old.mp4",status:"completed"});db.saveJob({...base,id:"old-queued",createdAt:"2020-01-01T00:00:00.000Z",updatedAt:"2020-01-01T00:00:00.000Z",sourceUrl:"https://example.com/queued.mp4",status:"queued"});expect(db.deleteTerminalBefore("2021-01-01T00:00:00.000Z")).toBe(1);expect(db.getJob("old-complete")).toBeUndefined();expect(db.getJob("old-queued")?.status).toBe("queued");db.close();});
  it("keeps only the newest configured database backups",async()=>{const dir=await root("svp-retention-backup-");const db=new AppDatabase(dir);for(let index=0;index<4;index++){const file=path.join(dir,`super-video-pro.sqlite.backup-${index}`);await fs.writeFile(file,String(index));await fs.utimes(file,new Date(2020,index,1),new Date(2020,index,1));}expect(db.pruneBackups(2)).toBe(2);expect((await fs.readdir(dir)).filter(name=>name.includes(".backup-")).sort()).toEqual(["super-video-pro.sqlite.backup-2","super-video-pro.sqlite.backup-3"]);db.close();});
  it("prunes expired daily logs and exports retained lines",async()=>{const dir=await root("svp-retention-log-");const old=path.join(dir,"app-2020-01-01.jsonl");await fs.writeFile(old,'{"time":"2020-01-01T00:00:00.000Z","level":"info","event":"old","details":{}}\n');await fs.utimes(old,new Date(2020,0,1),new Date(2020,0,1));const diagnostics=new Diagnostics(dir,30);diagnostics.write("info","kept",{});expect(await fs.stat(old).then(()=>true,()=>false)).toBe(false);const exported=path.join(dir,"debug.txt");diagnostics.exportText(exported);expect(await fs.readFile(exported,"utf8")).toContain("kept");});
});
