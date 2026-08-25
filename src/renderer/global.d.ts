import type { IpcChannel } from "../shared/ipc";
declare global { interface Window { superVideo: { invoke(channel:IpcChannel,input?:unknown):Promise<{ok:true;data:unknown}|{ok:false;error:{message:string;code:string}}> ;onJobsChanged(callback:(job:unknown)=>void):()=>void;onCompositionsChanged(callback:(job:unknown)=>void):()=>void } } }
declare module "*.css";
declare module "*.png";
export {};
