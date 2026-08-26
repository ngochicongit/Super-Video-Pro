import {describe,expect,it} from "vitest";
import {buildTimelineRows,frameSnap,reorderByTimelineStart} from "../src/renderer/timeline-adapter";

describe("professional timeline adapter",()=>{
  it("maps sequential video, audio and overlay actions to one timebase",()=>{const rows=buildTimelineRows([{id:"a",trimStart:1,trimEnd:5,speed:2},{id:"b",trimStart:0,trimEnd:3,speed:1}],{id:"music",duration:9},[{id:"mark",timelineStart:1,timelineEnd:4}],5,{videoLocked:false,audioLocked:false,overlayLocked:false});expect(rows[0]!.actions.map(action=>[action.start,action.end])).toEqual([[0,2],[2,5]]);expect(rows[1]!.actions[0]!.end).toBe(5);expect(rows[2]!.actions[0]).toMatchObject({start:1,end:4});});
  it("uses frame snapping and deterministic timeline reorder",()=>{expect(frameSnap(1.019)).toBe(1.0333333333333334);expect(reorderByTimelineStart([{id:"a"},{id:"b"},{id:"c"}],"c",.2,[1,1,1]).map(item=>item.id)).toEqual(["c","a","b"]);});
});
