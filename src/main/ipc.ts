import {ipcMain} from "electron";
import { ipcContract, type IpcChannel } from "../shared/ipc.js";
import { normalizeError } from "../shared/errors.js";
import type { JobManager } from "./jobs.js";
import type { Diagnostics } from "./diagnostics.js";
import type {AppUpdater} from "./app-updater.js";
import {appHandlers} from "./ipc-app-handlers.js";
import {jobHandlers} from "./ipc-job-handlers.js";
import {runtimeHandlers} from "./ipc-runtime-handlers.js";

export function registerIpc(jobs: JobManager,diagnostics:Diagnostics,updater:AppUpdater) {
  const handlers={...appHandlers(jobs,diagnostics),...jobHandlers(jobs),...runtimeHandlers(updater)};
  for (const channel of Object.keys(ipcContract) as IpcChannel[]) ipcMain.handle(channel, async (event, raw) => {
    try { const input=ipcContract[channel].input.parse(raw);const handler=handlers[channel] as (value:unknown,event?:Electron.IpcMainInvokeEvent)=>unknown|Promise<unknown>;const output=await handler(input,event); return {ok:true,data:ipcContract[channel].output.parse(output)}; }
    catch(error){ return {ok:false,error:normalizeError(error,"input")}; }
  });
}
