import type {DownloadJob} from "../shared/contracts";
import {useMemo} from "react";
import {api} from "./api";
import {t} from "./i18n";
import {JobRow,statusKeys} from "./job-row";
import {useAppStore} from "./store";
export function JobQueue({filter,setFilter,query,setQuery,scope="all"}:{filter:"all"|DownloadJob["status"];setFilter:(value:"all"|DownloadJob["status"])=>void;query:string;setQuery:(value:string)=>void;scope?:"all"|"active"|"history"}){
  const {jobs,loading,error,load,clearTerminal}=useAppStore();
  const visibleJobs=useMemo(()=>jobs.filter(job=>{const terminal=["completed","failed","cancelled"].includes(job.status);return(scope==="all"||(scope==="history"?terminal:!terminal))&&(filter==="all"||job.status===filter)&&`${job.resource?.title??""} ${job.sourceUrl}`.toLowerCase().includes(query.trim().toLowerCase())}),[jobs,filter,query,scope]);
  const terminalCount=jobs.filter(job=>["completed","cancelled"].includes(job.status)).length;
  const filterStatuses=(scope==="active"?["queued","running","paused","retrying","processing","validating"]:scope==="history"?["completed","failed","cancelled"]:Object.keys(statusKeys)) as DownloadJob["status"][];
  return <>{error&&<div className="alert"><span>{error}</span><button onClick={()=>load()}>{t("retry")}</button></div>}<section className="heading"><div><h2>{scope==="history"?t("download_history"):t("download_tasks")}</h2><p>{visibleJobs.length} {t("shown")}</p></div><div className="queue-tools"><input value={query} onChange={event=>setQuery(event.target.value)} onBlur={()=>void api.app.logAction("queue.search",{length:query.length})} placeholder={t("search_queue")}/><select value={filter} onChange={event=>{const value=event.target.value as typeof filter;setFilter(value);void api.app.logAction("queue.filter",{status:value});}}><option value="all">{t("all_statuses")}</option>{filterStatuses.map(status=><option key={status} value={status}>{t(statusKeys[status])}</option>)}</select>{scope==="history"&&<button className="refresh danger" disabled={!terminalCount} onClick={()=>clearTerminal()}>{t("clear_finished")} ({terminalCount})</button>}</div></section><section className="jobs">{loading&&!jobs.length?<div className="empty">{t("loading_queue")}</div>:visibleJobs.length?visibleJobs.map(job=><JobRow key={job.id} job={job}/>):<div className="empty"><strong>{t(scope==="history"?"history_empty":"active_tasks_empty")}</strong></div>}</section></>;
}
