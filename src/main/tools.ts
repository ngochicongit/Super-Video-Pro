import { spawn } from "node:child_process";import fs from "node:fs";import path from "node:path";
import readline from "node:readline";

export type ToolResult = { stdout:string; stderr:string; code:number };
export function resolveTool(command:string){if(process.platform!=="win32")return command;const exe=command.endsWith(".exe")?command:`${command}.exe`;const roots=[process.env.SVP_TOOL_DIR??"",typeof process.resourcesPath==="string"?path.join(process.resourcesPath,"tools"):"",path.resolve("vendor/tools")].filter(Boolean);for(const root of roots){const candidate=path.join(root,exe);if(fs.existsSync(candidate))return candidate}return command;}
export function runTool(command:string,args:string[],options:{signal?:AbortSignal;onLine?:(line:string)=>void;cwd?:string}={}):Promise<ToolResult>{
  return new Promise((resolve,reject)=>{const child=spawn(resolveTool(command),args,{windowsHide:true,stdio:["ignore","pipe","pipe"],cwd:options.cwd,detached:process.platform!=="win32"});let stdout="",stderr="",aborted=false;
    const abort=()=>{aborted=true;if(child.pid){if(process.platform==="win32")spawn("taskkill",["/pid",String(child.pid),"/T","/F"],{windowsHide:true,stdio:"ignore"});else try{process.kill(-child.pid,"SIGTERM")}catch{child.kill("SIGTERM")}}};
    if(options.signal?.aborted)abort();else options.signal?.addEventListener("abort",abort,{once:true});
    readline.createInterface({input:child.stdout}).on("line",line=>{stdout+=line+"\n";options.onLine?.(line)});readline.createInterface({input:child.stderr}).on("line",line=>{stderr+=line+"\n";options.onLine?.(line)});
    child.once("error",reject);child.once("close",code=>{options.signal?.removeEventListener("abort",abort);if(aborted)reject(Object.assign(new Error("The operation was aborted"),{name:"AbortError",code:"ABORT_ERR"}));else resolve({stdout,stderr,code:code??-1})});});
}
export function ytDlpRuntimeArgs(){const deno=resolveTool("deno");return deno==="deno"?["--js-runtimes","deno"]:["--js-runtimes",`deno:${deno}`];}
export function ytDlpSiteArgs(sourceUrl:string){try{const host=new URL(sourceUrl).hostname.toLowerCase();return host==="youtu.be"||host==="youtube.com"||host.endsWith(".youtube.com")?["--extractor-args","youtube:player_client=web_embedded"]:[]}catch{return []}}
export async function toolAvailable(command:string){try{return (await runTool(command,[command.startsWith("ff")?"-version":"--version"])).code===0}catch{return false}}
