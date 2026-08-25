import type {CompositionManager} from "./composition.js";
import type {IpcInput} from "./ipc-input.js";
export function compositionHandlers(manager:CompositionManager){return{
  "compositions:list":()=>manager.list(),
  "compositions:create":(input:IpcInput<"compositions:create">)=>manager.create(input),
  "compositions:cancel":(input:IpcInput<"compositions:cancel">)=>manager.command(input.compositionId,"cancel"),
  "compositions:retry":(input:IpcInput<"compositions:retry">)=>manager.command(input.compositionId,"retry")
  ,"compositions:remove":(input:IpcInput<"compositions:remove">)=>({removed:manager.remove(input.compositionId)})
};}
