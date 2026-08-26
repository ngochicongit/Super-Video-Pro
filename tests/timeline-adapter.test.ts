import {describe,expect,it} from "vitest";
import {boundedOverlayCenter,buildTimelineRows,frameSnap,previewAnimationDuration,reorderByTimelineStart,resizeSourceClip} from "../src/renderer/timeline-adapter";

describe("professional timeline adapter",()=>{
  it("maps sequential video, audio and overlay actions to one timebase",()=>{const rows=buildTimelineRows([{id:"a",trimStart:1,trimEnd:5,speed:2},{id:"b",trimStart:0,trimEnd:3,speed:1}],{id:"music",duration:9},[{id:"mark",timelineStart:1,timelineEnd:4}],5,{videoLocked:false,audioLocked:false,overlayLocked:false});expect(rows[0]!.actions.map(action=>[action.start,action.end])).toEqual([[0,2],[2,5]]);expect(rows[1]!.actions[0]!.end).toBe(5);expect(rows[2]!.actions[0]).toMatchObject({start:1,end:4});});
  it("uses frame snapping and deterministic timeline reorder",()=>{expect(frameSnap(1.019)).toBe(1.0333333333333334);expect(reorderByTimelineStart([{id:"a"},{id:"b"},{id:"c"}],"c",.2,[1,1,1]).map(item=>item.id)).toEqual(["c","a","b"]);});
  it("maps timeline edge resize back to source trim at clip speed",()=>{const clip={id:"a",duration:10,trimStart:2,trimEnd:8,speed:2};expect(resizeSourceClip(clip,1,4,1.5,4,"left").trimStart).toBe(3);expect(resizeSourceClip(clip,1,4,1,5,"right").trimEnd).toBe(10);expect(resizeSourceClip(clip,1,4,1,9,"right").trimEnd).toBe(10);});
  it("keeps the whole overlay inside its video frame",()=>{const frame={left:100,top:50,width:800,height:450},image={width:160,height:90};expect(boundedOverlayCenter(0,0,frame,image)).toEqual({x:10,y:10});expect(boundedOverlayCenter(1000,800,frame,image)).toEqual({x:90,y:90});});
  it("makes higher movement speed produce a shorter preview cycle",()=>{const bounds={width:800,height:450};expect(previewAnimationDuration(bounds,20,"horizontal",400,100)).toBeLessThan(previewAnimationDuration(bounds,20,"horizontal",100,100));expect(previewAnimationDuration(bounds,20,"vertical",100,400)).toBeLessThan(previewAnimationDuration(bounds,20,"vertical",100,100));});
});
