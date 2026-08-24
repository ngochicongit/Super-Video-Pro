import fs from "node:fs/promises";
import {createWriteStream} from "node:fs";
import {Readable} from "node:stream";
import {pipeline} from "node:stream/promises";
import type {MediaResource} from "../../shared/contracts.js";
import type {Progress} from "../download-types.js";
import {outputName,releaseOutput,reserveOutput} from "../download-output.js";
import {assertOutboundUrl} from "../network-policy.js";

export async function downloadHttp(resource:MediaResource,destinationDir:string,signal:AbortSignal,onProgress:(value:Progress)=>void){
  const variant=resource.variants[0];if(!variant||variant.protocol!=="http")throw new Error("Selected variant requires an external engine");assertOutboundUrl(variant.url);await fs.mkdir(destinationDir,{recursive:true});
  const final=await reserveOutput(destinationDir,outputName(resource));const partial=`${final}.part`;let existing=0;try{existing=(await fs.stat(partial)).size;}catch{}
  const headers:Record<string,string>={};if(existing>0)headers.Range=`bytes=${existing}-`;
  try{const response=await fetch(variant.url,{headers,signal});if(!response.ok||!response.body)throw new Error(`Download HTTP ${response.status}`);if(existing>0&&response.status!==206){existing=0;await fs.rm(partial,{force:true});}const remaining=Number(response.headers.get("content-length"))||null;const total=remaining===null?null:existing+remaining;let downloaded=existing;const webBody=response.body as unknown as import("node:stream/web").ReadableStream;const body=Readable.fromWeb(webBody);body.on("data",(chunk:Buffer)=>{downloaded+=chunk.length;onProgress({bytesDownloaded:downloaded,totalBytes:total});});await pipeline(body,createWriteStream(partial,{flags:existing>0?"a":"w"}));await fs.rename(partial,final);const stat=await fs.stat(final);return{path:final,size:stat.size};}
  finally{releaseOutput(final);}
}
