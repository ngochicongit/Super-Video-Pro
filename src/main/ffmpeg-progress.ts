export function parseFfmpegTime(value:string){
  const parts=value.trim().split(":").map(Number);
  if(parts.length!==3||parts.some(part=>!Number.isFinite(part)))return null;
  return parts[0]!*3600+parts[1]!*60+parts[2]!;
}

export function parseFfmpegProgressLine(line:string){
  if(line.startsWith("out_time_us=")){const value=Number(line.slice(12));return Number.isFinite(value)?value/1_000_000:null;}
  if(line.startsWith("out_time_ms=")){const value=Number(line.slice(12));return Number.isFinite(value)?value/1_000_000:null;}
  if(line.startsWith("out_time="))return parseFfmpegTime(line.slice(9));
  return null;
}
