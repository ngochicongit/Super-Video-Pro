import {useState} from "react";
import iconUrl from "../../assets/icon.png";
import {api} from "./api";
import {t} from "./i18n";
import {useAppStore} from "./store";

export function WindowBar({version}:{version:string}){
  const [maximized,setMaximized]=useState(false);
  const settings=useAppStore(state=>state.settings);const saveSettings=useAppStore(state=>state.saveSettings);
  async function control(action:"minimize"|"toggle-maximize"|"close"){void api.app.logAction("window.control",{action});const state=await api.app.windowControl(action);setMaximized(state.maximized);}
  return <div className="window-bar"><div className="window-title"><img src={iconUrl}/><span>{t("app_name")}</span><small>v{version||"..."}</small></div><label className="window-provider-consent" title={t("x_fallback_disclosure")}><input type="checkbox" checked={settings?.allowThirdPartyXFallback??false} onChange={event=>void saveSettings({allowThirdPartyXFallback:event.target.checked})}/><span>{t("allow_x_fallback")}</span><small>{t("x_fallback_disclosure")}</small></label><div className="traffic-controls"><button className="traffic minimize" aria-label={t("window_minimize")} title={t("window_minimize")} onClick={()=>control("minimize")}/><button className={`traffic maximize${maximized?" restored":""}`} aria-label={maximized?t("window_restore"):t("window_maximize")} title={maximized?t("window_restore"):t("window_maximize")} onClick={()=>control("toggle-maximize")}/><button className="traffic close" aria-label={t("window_close")} title={t("window_close")} onClick={()=>control("close")}/></div></div>;
}
