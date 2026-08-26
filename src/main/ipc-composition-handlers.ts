import {inspectCompositionInput,type CompositionManager} from "./composition.js";
import type {IpcInput} from "./ipc-input.js";
import {app} from "electron";
import path from "node:path";
import {ensureWaveform} from "./waveform-cache.js";
export function compositionHandlers(manager:CompositionManager){return{
  "compositions:list":()=>manager.list(),
  "compositions:inspect-file":async(input:IpcInput<"compositions:inspect-file">)=>{const value=await inspectCompositionInput(input.path);return{duration:value.duration,width:value.width,height:value.height,kinds:[...value.kinds]};},
  "compositions:waveform":async(input:IpcInput<"compositions:waveform">)=>({path:await ensureWaveform(input.path,path.join(app.getPath("userData"),"waveforms"))}),
  "compositions:create":(input:IpcInput<"compositions:create">)=>manager.create(input),
  "compositions:cancel":(input:IpcInput<"compositions:cancel">)=>manager.command(input.compositionId,"cancel"),
  "compositions:retry":(input:IpcInput<"compositions:retry">)=>manager.command(input.compositionId,"retry")
  ,"compositions:remove":(input:IpcInput<"compositions:remove">)=>({removed:manager.remove(input.compositionId)})
};}
