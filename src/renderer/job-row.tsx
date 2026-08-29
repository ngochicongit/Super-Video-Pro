import type {DownloadJob} from "../shared/contracts";
import {api} from "./api";
import {t,type TranslationKey} from "./i18n";
import {useAppStore} from "./store";

export const statusKeys:Record<DownloadJob["status"],TranslationKey>={queued:"status_queued",running:"status_running",paused:"status_paused",retrying:"status_retrying",processing:"status_processing",validating:"status_validating",failed:"status_failed",completed:"status_completed",cancelled:"status_cancelled"};
function formatBytes(n:number){if(!n)return "0 B";const units=["B","KB","MB","GB"];const i=Math.min(Math.floor(Math.log(n)/Math.log(1024)),3);return `${(n/1024**i).toFixed(i?1:0)} ${units[i]}`;}
const errorKeys:Record<string,TranslationKey>={INVALID_INPUT:"error_invalid_input",UNSUPPORTED_MEDIA:"error_unsupported_media",NETWORK_TIMEOUT:"error_network_timeout",LOW_DISK:"error_low_disk",TOOL_MISSING:"error_tool_missing",FINAL_INVALID:"error_final_invalid"};
export function jobErrorMessage(error:unknown){if(!error)return null;if(typeof error!=="object")return t("download_failed");const value=error as {code?:unknown;message?:unknown};if(typeof value.code==="string"&&errorKeys[value.code])return t(errorKeys[value.code]);const message=typeof value.message==="string"?value.message:"";if(/cookie database|could not copy.*cookie/i.test(message))return t("error_cookie_locked");if(/403|forbidden|provider|service unavailable/i.test(message))return t("error_provider_unavailable");return message||t("download_failed");}

export function JobRow({job}:{job:DownloadJob}){
  const command=useAppStore(state=>state.command);const remove=useAppStore(state=>state.remove);
  const action=job.status==="running"?"pause":job.status==="paused"?"resume":job.status==="failed"?"retry":null;
  const terminal=["completed","cancelled"].includes(job.status);
  const errorMessage=jobErrorMessage(job.error);
  async function showFile(){if(!job.downloadedPath)return;void api.app.logAction("file.reveal",{jobId:job.id});await api.app.showItem(job.downloadedPath);}
  const progress=Math.round(Math.max(0,Math.min(1,job.progress))*100);
  return <article className="job"><div className="job-top"><div><h3>{job.resource?.title??job.sourceUrl}</h3><p>{job.downloadedPath??job.destinationDir}</p></div><span className={`status ${job.status}`}>{t(statusKeys[job.status])}</span></div><div className="bar" role="progressbar" aria-label={`Tiến trình ${job.resource?.title??job.sourceUrl}`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={progress}><i style={{width:`${progress}%`}}/></div><div className="job-bottom"><span>{progress}% / {formatBytes(job.bytesDownloaded)}{job.totalBytes?` / ${formatBytes(job.totalBytes)}`:""}</span><div>{job.downloadedPath&&<button className="quiet" onClick={showFile}>{t("show_file")}</button>}{action&&<button onClick={()=>command(action,job.id)}>{t(action)}</button>}{!terminal&&<button className="quiet" onClick={()=>command("cancel",job.id)}>{t("cancel")}</button>}{terminal&&<button className="quiet danger" onClick={()=>remove(job.id)}>{t("remove")}</button>}</div></div>{errorMessage&&<p className="error">{errorMessage}</p>}</article>;
}
