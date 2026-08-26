export type VideoEdit={path:string;trimStart:number;trimEnd?:number;speed:number};
export type CompositionArgsInput={videoPaths:string[];videoEdits?:VideoEdit[];audioPath:string;audioVolume?:number;logos?:LogoOverlay[];logoPath?:string;tempPath:string;width:number;height:number};
export type LogoOverlay={path:string;mode:"static"|"bounce"|"horizontal"|"vertical";position:string;xPercent?:number;yPercent?:number;width:number;opacity:number;speedX:number;speedY:number;hue?:number;backgroundColor?:string;backgroundOpacity?:number;padding?:number;staticEffect?:"none"|"fade-in";fadeDuration?:number;timelineStart?:number;timelineEnd?:number};
function bounce(axis:"x"|"y",speed:number){const outer=axis==="x"?"W-w":"H-h";return `if(lt(mod(t*${speed},2*(${outer})),${outer}),mod(t*${speed},2*(${outer})),2*(${outer})-mod(t*${speed},2*(${outer})))`;}
export function logoOverlayFilter(logos:LogoOverlay[],videoLabel="vbase",startIndex=0){
  return logos.map((logo,index)=>{
    const input=startIndex+index;const source=index?`logoout${index-1}`:videoLabel;const color=(logo.backgroundColor??"#000000").replace("#","0x");
    const chain=[`scale='min(${logo.width},iw)':-1`,logo.hue?`hue=h=${logo.hue}`:"null","format=rgba",logo.padding?`pad=iw+${logo.padding*2}:ih+${logo.padding*2}:${logo.padding}:${logo.padding}:color=${color}@${logo.backgroundOpacity??0}`:"null",`colorchannelmixer=aa=${logo.opacity}`,logo.staticEffect==="fade-in"?`fade=t=in:st=0:d=${logo.fadeDuration??1}:alpha=1`:"null"].join(",");
    const [vertical,horizontal]=logo.position.split("-").length===2?logo.position.split("-"):[logo.position,logo.position];
    const fixedX=logo.xPercent===undefined?(horizontal==="left"?"24":horizontal==="right"?"W-w-24":"(W-w)/2"):`(W-w)*${logo.xPercent}/100`;
    const fixedY=logo.yPercent===undefined?(vertical==="top"?"24":vertical==="bottom"?"H-h-24":"(H-h)/2"):`(H-h)*${logo.yPercent}/100`;
    const movingX=logo.mode==="bounce"||logo.mode==="horizontal";const movingY=logo.mode==="bounce"||logo.mode==="vertical";
    const x=movingX?bounce("x",logo.speedX):fixedX;const y=movingY?bounce("y",logo.speedY):fixedY;
    const timing=logo.timelineEnd===undefined&&!(logo.timelineStart??0)?"":`:enable='between(t,${logo.timelineStart??0},${logo.timelineEnd??86400})'`;
    const overlay=movingX||movingY?`overlay=x='${x}':y='${y}'${timing}`:`overlay=${x}:${y}${timing}`;
    return `[${input}:v:0]${chain}[logo${index}];[${source}][logo${index}]${overlay}[logoout${index}]`;
  }).join(";");
}

export function compositionArgs(input:CompositionArgsInput){
  const {videoPaths,audioPath,tempPath,width,height}=input; const logos=input.logos??(input.logoPath?[{path:input.logoPath,mode:"static",position:"bottom-right",width:220,opacity:1,speedX:120,speedY:90}]:[]);const edits:VideoEdit[]=input.videoEdits??videoPaths.map(path=>({path,trimStart:0,speed:1}));const edited=edits.some(item=>item.trimStart||item.trimEnd!==undefined||item.speed!==1);const audioArgs=input.audioVolume===undefined||input.audioVolume===1?[]:["-af",`volume=${input.audioVolume}`];
  const videoInputs=videoPaths.flatMap(file=>["-i",file]);
  const audioIndex=videoPaths.length;
  const logoIndex=audioIndex+1;
  if(videoPaths.length===1&&!logos.length&&!edited)return["-y",...videoInputs,"-i",audioPath,"-map","0:v:0","-map",`${audioIndex}:a:0`,"-c:v","copy","-c:a","aac",...audioArgs,"-shortest","-f","mp4",tempPath];
  const inputs=[...videoInputs,"-i",audioPath,...logos.flatMap(logo=>["-i",logo.path])];
  const normalized=videoPaths.map((_,index)=>{const edit:VideoEdit=edits[index]??{path:videoPaths[index]!,trimStart:0,speed:1};const trim=`trim=start=${edit.trimStart}${edit.trimEnd===undefined?"":`:end=${edit.trimEnd}`},setpts=(PTS-STARTPTS)/${edit.speed}`;return `[${index}:v:0]${trim},scale=${width}:${height}:force_original_aspect_ratio=decrease,pad=${width}:${height}:(ow-iw)/2:(oh-ih)/2,setsar=1[v${index}]`;}).join(";");
  const concat=videoPaths.length===1?"[v0]null[vbase]":`${videoPaths.map((_,index)=>`[v${index}]`).join("")}concat=n=${videoPaths.length}:v=1:a=0[vbase]`;
  const filter=`${normalized};${concat}${logos.length?`;${logoOverlayFilter(logos,"vbase",logoIndex)}`:""}`;
  return["-y",...inputs,"-filter_complex",filter,"-map",logos.length?`[logoout${logos.length-1}]`:"[vbase]","-map",`${audioIndex}:a:0`,"-c:v","libx264","-pix_fmt","yuv420p","-c:a","aac",...audioArgs,"-shortest","-f","mp4",tempPath];
}
