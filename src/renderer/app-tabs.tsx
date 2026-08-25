import {t} from "./i18n";
export type AppTab="download"|"composition"|"tasks"|"history"|"settings";
const tabs:AppTab[]=["download","composition","tasks","history","settings"];
export function AppTabs({active,onChange}:{active:AppTab;onChange:(tab:AppTab)=>void}){return <nav className="app-tabs" aria-label={t("navigation")} role="tablist">{tabs.map(tab=><button key={tab} data-tab={tab} role="tab" aria-selected={active===tab} className={active===tab?"active":""} onClick={()=>onChange(tab)}>{t(`tab_${tab}`)}</button>)}</nav>}
