// AiCut-inspired boundary: one canonical timebase and one transaction per pointer gesture.
// This is an original adapter for Super Video Pro; no AiCut source file is vendored.
export type TimelineClip={id:string;trimStart:number;trimEnd:number;speed:number;duration?:number};
export type TimelineLogo={id:string;timelineStart:number;timelineEnd?:number};
export type TimelineActionShape={id:string;start:number;end:number;effectId:string;selected?:boolean;flexible?:boolean;movable?:boolean};
export type TimelineRowShape={id:string;actions:TimelineActionShape[];rowHeight?:number;classNames?:string[]};

export const editedDuration=(clip:TimelineClip)=>Math.max(1/30,(clip.trimEnd-clip.trimStart)/clip.speed);

export function buildTimelineRows(clips:TimelineClip[],audio:{id:string;duration:number}|null,logos:TimelineLogo[],duration:number,locks:{videoLocked:boolean;audioLocked:boolean;overlayLocked:boolean},selectedId?:string):TimelineRowShape[]{
  let cursor=0;const videoActions=clips.map(clip=>{const start=cursor,end=start+editedDuration(clip);cursor=end;return{id:`video:${clip.id}`,start,end,effectId:"video",selected:selectedId===clip.id,flexible:!locks.videoLocked,movable:!locks.videoLocked};});
  return[
    {id:"video",rowHeight:52,classNames:[locks.videoLocked?"locked":""],actions:videoActions},
    {id:"audio",rowHeight:52,classNames:[locks.audioLocked?"locked":""],actions:audio?[{id:`audio:${audio.id}`,start:0,end:Math.min(Math.max(duration,1/30),audio.duration),effectId:"audio",selected:selectedId===audio.id,flexible:false,movable:false}]:[]},
    {id:"overlay",rowHeight:52,classNames:[locks.overlayLocked?"locked":""],actions:logos.map(logo=>({id:`logo:${logo.id}`,start:Math.max(0,logo.timelineStart),end:Math.max(logo.timelineStart+1/30,Math.min(duration,logo.timelineEnd??duration)),effectId:"logo",selected:selectedId===logo.id,flexible:!locks.overlayLocked,movable:!locks.overlayLocked}))}
  ];
}

export function reorderByTimelineStart<T extends {id:string}>(items:T[],id:string,start:number,durations:number[]){
  const from=items.findIndex(item=>item.id===id);if(from<0)return items;const remaining=items.filter(item=>item.id!==id);let cursor=0,to=0;for(;to<remaining.length;to++){const originalIndex=items.findIndex(item=>item.id===remaining[to]!.id);const length=durations[originalIndex]??0;if(start<cursor+length/2)break;cursor+=length;}const next=[...remaining];next.splice(to,0,items[from]!);return next;
}

export const frameSnap=(seconds:number,fps=30)=>Math.round(seconds*fps)/fps;

export function resizeSourceClip<T extends TimelineClip>(clip:T,actionStart:number,actionEnd:number,nextStart:number,nextEnd:number,dir:"left"|"right"):T{
  if(dir==="left"){const trimStart=Math.max(0,Math.min(clip.trimEnd-1/30,clip.trimStart+(nextStart-actionStart)*clip.speed));return{...clip,trimStart};}
  const trimEnd=Math.min(clip.duration??Number.POSITIVE_INFINITY,Math.max(clip.trimStart+1/30,clip.trimEnd+(nextEnd-actionEnd)*clip.speed));return{...clip,trimEnd};
}

export function boundedOverlayCenter(clientX:number,clientY:number,frame:{left:number;top:number;width:number;height:number},image:{width:number;height:number}){const halfX=Math.min(50,image.width/frame.width*50),halfY=Math.min(50,image.height/frame.height*50);return{x:Math.max(halfX,Math.min(100-halfX,(clientX-frame.left)/frame.width*100)),y:Math.max(halfY,Math.min(100-halfY,(clientY-frame.top)/frame.height*100))};}

export function previewAnimationDuration(bounds:{width:number;height:number},logoWidthPercent:number,mode:"static"|"bounce"|"horizontal"|"vertical",speedX:number,speedY:number){const width=Math.max(1,bounds.width*(1-logoWidthPercent/100)),height=Math.max(1,bounds.height*.55);if(mode==="horizontal")return Math.max(.25,width/Math.max(1,speedX)*2);if(mode==="vertical")return Math.max(.25,height/Math.max(1,speedY)*2);return Math.max(.25,Math.max(width/Math.max(1,speedX),height/Math.max(1,speedY))*2);}
