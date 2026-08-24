import type {JobManager} from "./jobs.js";
import type {IpcInput} from "./ipc-input.js";

export function jobHandlers(jobs:JobManager){return {
  "media:inspect":(input:IpcInput<"media:inspect">)=>jobs.inspect(input.sourceUrl),
  "jobs:list":(input:IpcInput<"jobs:list">)=>jobs.list(input.limit),
  "jobs:create":(input:IpcInput<"jobs:create">)=>jobs.create(input),
  "jobs:pause":(input:IpcInput<"jobs:pause">)=>jobs.command(input.jobId,"pause"),
  "jobs:resume":(input:IpcInput<"jobs:resume">)=>jobs.command(input.jobId,"resume"),
  "jobs:cancel":(input:IpcInput<"jobs:cancel">)=>jobs.command(input.jobId,"cancel"),
  "jobs:retry":(input:IpcInput<"jobs:retry">)=>jobs.command(input.jobId,"retry"),
  "jobs:remove":(input:IpcInput<"jobs:remove">)=>jobs.remove(input.jobId),
  "jobs:clear-terminal":(input:IpcInput<"jobs:clear-terminal">)=>jobs.clearTerminal(input.statuses)
};}
