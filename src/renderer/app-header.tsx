import {useState} from "react";
import {api} from "./api";
import {t} from "./i18n";
import {useAppStore} from "./store";

function localizedUpdateMessage(result:{state:string;version?:string}){switch(result.state){case"checking":return t("update_checking");case"available":return `${t("update_available")}${result.version?`: ${result.version}`:""}`;case"not-available":return t("update_not_available");case"not-configured":return t("update_not_configured");default:return t("update_error");}}

export function AppHeader({debugFileName,setDebugFileName,updatesConfigured}:{debugFileName:string;setDebugFileName:(value:string)=>void;updatesConfigured:boolean}){
  const load=useAppStore(state=>state.load);const [updateMessage,setUpdateMessage]=useState("");
  async function checkUpdates(){void api.app.logAction("update.check");try{setUpdateMessage(t("update_checking"));setUpdateMessage(localizedUpdateMessage(await api.app.checkUpdates()));}catch{setUpdateMessage(t("update_error"));}}
  return <header className="hero"><div><span className="eyebrow">{t("tagline")}</span><h1>Super Video <b>Pro</b></h1>{updateMessage&&<span className="update-note">{updateMessage}</span>}</div><div className="header-actions">{updatesConfigured&&<button className="refresh" onClick={checkUpdates}>{t("check_updates")}</button>}<div className="diagnostics-export"><input value={debugFileName} onChange={event=>setDebugFileName(event.target.value)} placeholder={t("debug_name_placeholder")} maxLength={120}/><button className="refresh" onClick={()=>{void api.app.logAction("diagnostics.export");void api.app.exportDiagnostics(debugFileName);}}>{t("export_diagnostics")}</button></div><button className="refresh" onClick={()=>load()}>{t("refresh")}</button></div></header>;
}
