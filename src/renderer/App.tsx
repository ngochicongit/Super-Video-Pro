import {useEffect,useRef,useState} from "react";
import type {CompositionJob,DownloadJob,MediaResource} from "../shared/contracts";
import {api} from "./api";
import {AppHeader} from "./app-header";
import {AppTabs,type AppTab} from "./app-tabs";
import {CompositionBuilder} from "./composition-builder";
import {CompositionJobs} from "./composition-jobs";
import {DownloadComposer} from "./download-composer";
import {t} from "./i18n";
import {JobQueue} from "./job-queue";
import {SettingsPanel} from "./settings-panel";
import {useAppStore} from "./store";
import {hydratedUiState,recentUrlsWith} from "./ui-state";
import {WindowBar} from "./window-bar";
import {aggregateTaskProgress} from "./task-progress";

export function App(){
  const {settings,load,add,saveSettings,jobs}=useAppStore();
  const [url,setUrl]=useState("");const [resource,setResource]=useState<MediaResource>();const [selected,setSelected]=useState("");const [inspecting,setInspecting]=useState(false);const [inspectError,setInspectError]=useState("");const [batch,setBatch]=useState(false);const [tools,setTools]=useState<Array<{name:string;available:boolean;version:string|null}>>([]);const [filter,setFilter]=useState<"all"|DownloadJob["status"]>("all");const [query,setQuery]=useState("");const [version,setVersion]=useState("");const [updatesConfigured,setUpdatesConfigured]=useState(false);const [debugFileName,setDebugFileName]=useState("");const [tab,setTab]=useState<AppTab>("download");const [tasksOpen,setTasksOpen]=useState(false);const [settingsOpen,setSettingsOpen]=useState(false);const [compositionJobs,setCompositionJobs]=useState<CompositionJob[]>([]);const hydrated=useRef(false);
  const activeDownloadJobs=jobs.filter(job=>!["completed","failed","cancelled"].includes(job.status));
  const activeCompositionJobs=compositionJobs.filter(job=>!["completed","failed","cancelled"].includes(job.status));
  const activeJobs=[...activeDownloadJobs,...activeCompositionJobs];
  const taskProgress=aggregateTaskProgress(activeJobs);

  useEffect(()=>{void load();const unsubscribe=api.jobs.subscribe(job=>useAppStore.getState().upsertJob(job));void api.app.toolStatus().then(setTools);void api.app.info().then(info=>{setVersion(info.version);setUpdatesConfigured(info.updatesConfigured);});void api.app.logAction("app.renderer.ready");return unsubscribe;},[load]);
  useEffect(()=>{void api.compositions.list().then(setCompositionJobs);return api.compositions.subscribe(job=>setCompositionJobs(current=>[job,...current.filter(item=>item.id!==job.id)]));},[]);
  useEffect(()=>{if(!settings||hydrated.current)return;hydrated.current=true;const state=hydratedUiState(settings);setUrl(state.url);setBatch(state.batch);setQuery(state.query);setFilter(state.filter);setDebugFileName(state.debugFileName);},[settings]);
  useEffect(()=>{if(!hydrated.current||!settings?.rememberUiState)return;const timer=setTimeout(()=>void saveSettings({lastSourceInput:url,downloadMode:batch?"batch":"single",queueSearch:query,queueStatusFilter:filter,diagnosticsFileName:debugFileName}),450);return()=>clearTimeout(timer);},[url,batch,query,filter,debugFileName,settings?.rememberUiState,saveSettings]);
  useEffect(()=>{if(!tasksOpen&&!settingsOpen)return;const close=(event:KeyboardEvent)=>{if(event.key==="Escape"){setTasksOpen(false);setSettingsOpen(false);}};window.addEventListener("keydown",close);return()=>window.removeEventListener("keydown",close);},[tasksOpen,settingsOpen]);

  async function rememberUrl(source:string){await saveSettings({recentUrls:recentUrlsWith(source,settings?.recentUrls??[])});}
  async function inspect(){if(!url.trim())return;setInspecting(true);setInspectError("");void api.app.logAction("media.inspect.start");try{const source=url.trim();const parsed=new URL(source);if(["http:","https:"].includes(parsed.protocol))await rememberUrl(source);const found=await api.media.inspect(source);setResource(found);setSelected(found.variants[0]?.id??"");void api.app.logAction("media.inspect.success",{extractor:found.extractor,variants:found.variants.length});}catch(reason){setResource(undefined);setInspectError(reason instanceof Error?reason.message:String(reason));void api.app.logAction("media.inspect.failure");}finally{setInspecting(false);}}
  async function submit(event:React.FormEvent){event.preventDefault();if(batch){const urls=[...new Set(url.split(/\r?\n/).map(value=>value.trim()).filter(Boolean))];setInspecting(true);void api.app.logAction("batch.download.start",{count:urls.length});const failures:string[]=[];const accepted:string[]=[];for(const source of urls){try{const found=await api.media.inspect(source);await add(source,found,found.variants[0]?.id);accepted.push(source);}catch(reason){failures.push(`${source}: ${reason instanceof Error?reason.message:String(reason)}`);}}if(accepted.length)await saveSettings({recentUrls:[...accepted.reverse(),...(settings?.recentUrls??[]).filter(item=>!accepted.includes(item))].slice(0,30)});setInspectError(failures.join("\n"));setInspecting(false);void api.app.logAction("batch.download.finish",{count:urls.length,failures:failures.length});if(!failures.length)setUrl("");return;}if(!resource){await inspect();return;}await add(url.trim(),resource,selected||undefined);setUrl("");setResource(undefined);setSelected("");}
  function changeTab(next:AppTab){setTab(next);if(next==="history")setFilter("all");void api.app.logAction("navigation.tab",{tab:next});}
  function openTasks(){setSettingsOpen(false);setTasksOpen(true);setFilter("all");}
  function openSettings(){setTasksOpen(false);setSettingsOpen(true);}

  return <>
    <WindowBar version={version}/>
    <main aria-hidden={tasksOpen||settingsOpen||undefined} inert={tasksOpen||settingsOpen||undefined}>
      <AppHeader activeTasks={activeJobs.length} taskProgress={taskProgress} onTasks={openTasks} onSettings={openSettings}/>
      <AppTabs active={tab} onChange={changeTab}/>
      <section className="tab-panel" role="tabpanel">
        {tab==="download"&&<DownloadComposer url={url} setUrl={setUrl} resource={resource} setResource={setResource} selected={selected} setSelected={setSelected} inspecting={inspecting} inspectError={inspectError} setInspectError={setInspectError} batch={batch} setBatch={setBatch} inspect={inspect} submit={submit}/>}
        {tab==="composition"&&<CompositionBuilder/>}
        {tab==="history"&&<><header className="page-heading"><h2>{t("tab_history")}</h2><p>{t("history_hint")}</p></header><JobQueue scope="history" filter={filter} setFilter={setFilter} query={query} setQuery={setQuery}/><CompositionJobs scope="history"/></>}
      </section>
    </main>
    {tasksOpen&&<div className="surface-backdrop" onPointerDown={()=>setTasksOpen(false)}><aside className="task-drawer" role="dialog" aria-modal="true" aria-labelledby="task-drawer-title" data-open-surface="tasks" onPointerDown={event=>event.stopPropagation()}><header><div><span>TỔNG QUAN</span><h2 id="task-drawer-title">Tác vụ đang chạy</h2>{activeJobs.length>0&&<div className="drawer-progress" role="progressbar" aria-label="Tổng tiến trình tác vụ" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(taskProgress*100)}><i style={{width:`${Math.round(taskProgress*100)}%`}}/><small>{Math.round(taskProgress*100)}%</small></div>}</div><button aria-label="Đóng tác vụ" onClick={()=>setTasksOpen(false)}>×</button></header><div className="surface-scroll"><JobQueue scope="active" filter={filter} setFilter={setFilter} query={query} setQuery={setQuery}/><CompositionJobs scope="active"/></div></aside></div>}
    {settingsOpen&&<div className="surface-backdrop centered" onPointerDown={()=>setSettingsOpen(false)}><section className="settings-modal" role="dialog" aria-modal="true" aria-labelledby="settings-modal-title" data-open-surface="settings" onPointerDown={event=>event.stopPropagation()}><header><div><span>TÙY CHỈNH ỨNG DỤNG</span><h2 id="settings-modal-title">Cài đặt</h2></div><button aria-label="Đóng cài đặt" onClick={()=>setSettingsOpen(false)}>×</button></header><div className="surface-scroll"><SettingsPanel tools={tools} debugFileName={debugFileName} setDebugFileName={setDebugFileName} updatesConfigured={updatesConfigured}/></div></section></div>}
  </>;
}
