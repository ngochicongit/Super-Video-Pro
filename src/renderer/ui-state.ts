import type {AppSettings} from "../shared/contracts";

export function hydratedUiState(settings:AppSettings){return settings.rememberUiState?{url:settings.lastSourceInput,batch:settings.downloadMode==="batch",query:settings.queueSearch,filter:settings.queueStatusFilter,debugFileName:settings.diagnosticsFileName}:{url:"",batch:false,query:"",filter:"all" as const,debugFileName:settings.diagnosticsFileName};}
export function recentUrlsWith(source:string,current:string[]){return[source,...current.filter(item=>item!==source)].slice(0,30);}
export function recentUrlsWithout(source:string,current:string[]){return current.filter(item=>item!==source);}
export function forgottenUiStatePatch(){return{lastSourceInput:"",downloadMode:"single" as const,queueSearch:"",queueStatusFilter:"all" as const,diagnosticsFileName:""};}
