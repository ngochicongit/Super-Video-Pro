import type {DownloadJob} from "../shared/contracts";
import {useMemo} from "react";
import {api} from "./api";
import {t} from "./i18n";
import {JobRow,statusKeys} from "./job-row";
import {useAppStore} from "./store";

export function JobQueue({filter,setFilter,query,setQuery}:{filter:"all"|DownloadJob["status"];setFilter:(value:"all"|DownloadJob["status"])=>void;query:string;setQuery:(value:string)=>void}){
  const {jobs,loading,error,load,clearTerminal}=useAppStore();
  const visibleJobs=useMemo(()=>jobs.filter(job=>(filter==="all"||job.status===filter)&&`${job.resource?.title??""} ${job.sourceUrl}`.toLowerCase().includes(query.trim().toLowerCase())),[jobs,filter,query]);
  const terminalCount=jobs.filter(job=>["completed","cancelled"].includes(job.status)).length;
  return <>{error&&<div className="alert"><span>{error}</span><button onClick={()=>load()}>{t("retry")}</button></div>}<section className="heading"><div><h2>{t("queue")}</h2><p>{visibleJobs.length} {t("shown")} / {jobs.length} {t("total")}</p></div><div className="queue-tools"><input value={query} onChange={event=>setQuery(event.target.value)} onBlur={()=>void api.app.logAction("queue.search",{length:query.length})} placeholder={t("search_queue")}/><select value={filter} onChange={event=>{const value=event.target.value as typeof filter;setFilter(value);void api.app.logAction("queue.filter",{status:value});}}><option value="all">{t("all_statuses")}</option>{Object.keys(statusKeys).map(status=><option key={status} value={status}>{t(statusKeys[status as DownloadJob["status"]])}</option>)}</select><button className="refresh danger" disabled={!terminalCount} onClick={()=>clearTerminal()}>{t("clear_finished")} ({terminalCount})</button></div></section><section className="jobs">{loading&&!jobs.length?<div className="empty">{t("loading_queue")}</div>:visibleJobs.length?visibleJobs.map(job=><JobRow key={job.id} job={job}/>):<div className="empty"><strong>{jobs.length?t("no_matching_tasks"):t("queue_empty")}</strong><span>{jobs.length?t("change_filter"):t("empty_hint")}</span></div>}</section></>;
}
