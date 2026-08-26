import {app,BrowserWindow,dialog,shell} from "electron";
import type {Diagnostics} from "./diagnostics.js";
import type {JobManager} from "./jobs.js";
import type {IpcInput} from "./ipc-input.js";
import {diagnosticsBaseName} from "./diagnostics-name.js";
import type {ProductEvidence} from "./product-evidence.js";
import {anyUpdateCheckConfigured} from "./app-updater.js";

export function appHandlers(jobs:JobManager,diagnostics:Diagnostics,evidence:ProductEvidence){return {
  "app:get-info":()=>({version:app.getVersion(),platform:process.platform,updatesConfigured:anyUpdateCheckConfigured()}),
  "settings:get":()=>jobs.settings(),
  "settings:update":(input:IpcInput<"settings:update">)=>{const settings=jobs.updateSettings(input);diagnostics.setRetentionDays(settings.logRetentionDays);return settings;},
  "dialog:download-dir":async()=>{const result=await dialog.showOpenDialog({properties:["openDirectory","createDirectory"]});return result.canceled?null:result.filePaths[0]??null;},
  "dialog:composition-input":async(input:IpcInput<"dialog:composition-input">)=>{const filters=input.kind==="video"?[{name:"Video",extensions:["mp4","mkv","mov","webm","avi"]}]:[{name:"Audio",extensions:["mp3","m4a","aac","wav","flac","ogg"]}];const result=await dialog.showOpenDialog({properties:["openFile"],filters});return result.canceled?null:result.filePaths[0]??null;},
  "dialog:composition-logo":async()=>{const result=await dialog.showOpenDialog({properties:["openFile"],filters:[{name:"Logo",extensions:["png","jpg","jpeg","webp"]}]});return result.canceled?null:result.filePaths[0]??null;},
  "dialog:composition-videos":async()=>{const result=await dialog.showOpenDialog({properties:["openFile","multiSelections"],filters:[{name:"Video",extensions:["mp4","mkv","mov","webm","avi"]}]});return result.canceled?[]:result.filePaths.slice(0,19);},
  "shell:show-item":async(input:IpcInput<"shell:show-item">)=>{shell.showItemInFolder(input.path);return{shown:true};},
  "window:control":(input:IpcInput<"window:control">,event?:Electron.IpcMainInvokeEvent)=>{const win=event?BrowserWindow.fromWebContents(event.sender):null;if(!win)throw new Error("Window is not available");if(input.action==="minimize")win.minimize();else if(input.action==="toggle-maximize")win.isMaximized()?win.unmaximize():win.maximize();else win.close();return{maximized:win.isMaximized()};},
  "app:log-action":(input:IpcInput<"app:log-action">)=>{diagnostics.write("info","ui.action",{action:input.action,details:input.details});return{logged:true};},
  "diagnostics:export":async(input:IpcInput<"diagnostics:export">)=>{const base=diagnosticsBaseName(input.fileName);const result=await dialog.showSaveDialog({title:"Export diagnostics",defaultPath:`${base}.txt`,filters:[{name:"Text",extensions:["txt"]}]});if(result.canceled||!result.filePath)return null;diagnostics.exportText(result.filePath);return result.filePath;}
  ,"evidence:gate":()=>evidence.gate()
  ,"evidence:multi-input-intent":()=>evidence.recordIfEnabled(jobs.settings().collectProductEvidence,"composition.multi_input_intent")
  ,"evidence:export":async()=>{const result=await dialog.showSaveDialog({title:"Export local product evidence",defaultPath:"super-video-pro-product-evidence.txt",filters:[{name:"Text",extensions:["txt"]}]});if(result.canceled||!result.filePath)return null;return evidence.exportText(result.filePath);}
};}
