import {describe,expect,it} from "vitest";
import {AppSettings} from "../src/shared/contracts";
import {forgottenUiStatePatch,hydratedUiState,recentUrlsWith,recentUrlsWithout} from "../src/renderer/ui-state";
import {diagnosticsBaseName} from "../src/main/diagnostics-name";

const settings=AppSettings.parse({downloadDir:"C:\\downloads",concurrency:2,perDomainConcurrency:1,cookiesFromBrowser:"none",rememberUiState:true,lastSourceInput:"https://example.com/a.mp4",downloadMode:"batch",queueSearch:"needle",queueStatusFilter:"failed",recentUrls:["https://example.com/a.mp4"],diagnosticsFileName:"session"});
describe("persistent UI state",()=>{
  it("hydrates all remembered controls together",()=>expect(hydratedUiState(settings)).toEqual({url:"https://example.com/a.mp4",batch:true,query:"needle",filter:"failed",debugFileName:"session"}));
  it("does not hydrate private controls when remembering is disabled",()=>expect(hydratedUiState({...settings,rememberUiState:false})).toEqual({url:"",batch:false,query:"",filter:"all",debugFileName:"session"}));
  it("bounds, deduplicates, recalls and removes recent links",()=>{const values=recentUrlsWith("https://example.com/a.mp4",["https://example.com/b.mp4","https://example.com/a.mp4"]);expect(values).toEqual(["https://example.com/a.mp4","https://example.com/b.mp4"]);expect(recentUrlsWithout("https://example.com/a.mp4",values)).toEqual(["https://example.com/b.mp4"]);expect(recentUrlsWith("https://example.com/new.mp4",Array.from({length:30},(_,index)=>`https://example.com/${index}.mp4`))).toHaveLength(30);});
  it("clears persisted controls on remember-state opt-out",()=>expect(forgottenUiStatePatch()).toEqual({lastSourceInput:"",downloadMode:"single",queueSearch:"",queueStatusFilter:"all",diagnosticsFileName:""}));
});
describe("diagnostics filename",()=>{it("uses the dated legacy fallback when blank",()=>expect(diagnosticsBaseName("",new Date("2026-08-25T00:00:00.000Z"))).toBe("super-video-pro-diagnostics-2026-08-25"));it("sanitizes a user-provided name",()=>expect(diagnosticsBaseName("my:debug.txt")).toBe("my_debug"));});
