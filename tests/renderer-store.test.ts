import {afterEach,describe,expect,it} from "vitest";
import {useAppStore} from "../src/renderer/store";
import type {DownloadJob} from "../src/shared/contracts";

const original=useAppStore.getState();
function job(id:string,createdAt:string,status:DownloadJob["status"]="queued"):DownloadJob{return{id,createdAt,updatedAt:createdAt,sourceUrl:`https://example.com/${id}.mp4`,destinationDir:"C:\\downloads",status,priority:50,attempts:0,maxAttempts:3,progress:0,bytesDownloaded:0,totalBytes:null};}

afterEach(()=>useAppStore.setState(original,true));
describe("event-driven renderer job state",()=>{
  it("inserts new jobs and keeps newest-first order",()=>{const state=useAppStore.getState();state.upsertJob(job("older","2026-01-01T00:00:00.000Z"));state.upsertJob(job("newer","2026-01-02T00:00:00.000Z"));expect(useAppStore.getState().jobs.map(item=>item.id)).toEqual(["newer","older"]);});
  it("replaces a changed job without duplicating it",()=>{const state=useAppStore.getState();state.upsertJob(job("same","2026-01-01T00:00:00.000Z"));state.upsertJob(job("same","2026-01-01T00:00:00.000Z","completed"));expect(useAppStore.getState().jobs).toHaveLength(1);expect(useAppStore.getState().jobs[0]?.status).toBe("completed");});
});
