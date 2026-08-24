import fs from "node:fs/promises";
import path from "node:path";
import type {MediaResource} from "../shared/contracts.js";

const reservedOutputs=new Set<string>();
export function outputName(resource:MediaResource,fallbackExtension=""){const variant=resource.variants[0];const raw=resource.title.replace(/[<>:"/\\|?*\x00-\x1F]/g,"_").slice(0,170)||"download";const extension=path.extname(new URL(variant?.url??resource.sourceUrl).pathname).slice(0,10)||fallbackExtension;return path.extname(raw)?raw:`${raw}${extension}`;}
export async function reserveOutput(destinationDir:string,name:string){const parsed=path.parse(name);for(let index=1;;index++){const candidate=path.join(destinationDir,index===1?name:`${parsed.name} (${index})${parsed.ext}`);const partial=`${candidate}.part`;let finalExists=false,partialExists=false;try{await fs.access(candidate);finalExists=true;}catch{}try{await fs.access(partial);partialExists=true;}catch{}if(!reservedOutputs.has(candidate)&&!finalExists&&(index===1&&partialExists||!partialExists)){reservedOutputs.add(candidate);return candidate;}}}
export function releaseOutput(filePath:string){reservedOutputs.delete(filePath);}
