import type {AppUpdater} from "./app-updater.js";
import {runTool,toolAvailable} from "./tools.js";

export function runtimeHandlers(updater:AppUpdater){return {
  "tools:status":async()=>Promise.all(["yt-dlp","deno","ffmpeg","ffprobe"].map(async name=>{const available=await toolAvailable(name);let version:string|null=null;if(available){const result=await runTool(name,[name.startsWith("ff")?"-version":"--version"]);version=(result.stdout||result.stderr).split(/\r?\n/)[0]?.trim()||null;}return{name,available,version};})),
  "updates:check":()=>updater.check(),
  "updates:status":()=>updater.status(),
  "updates:download":()=>updater.download(),
  "updates:install":()=>{updater.install();return{accepted:true};}
};}
