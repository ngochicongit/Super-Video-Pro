import { app, BrowserWindow, Notification } from "electron";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { AppUpdater } from "./app-updater.js";
import { runBrowserSmoke } from "./browser-smoke.js";
import { AppDatabase } from "./db.js";
import { Diagnostics } from "./diagnostics.js";
import { registerIpc } from "./ipc.js";
import { JobManager } from "./jobs.js";
import {ProductEvidence} from "./product-evidence.js";

const here=path.dirname(fileURLToPath(import.meta.url));
let db:AppDatabase|undefined;

async function createWindow(){
  const win=new BrowserWindow({width:1180,height:760,minWidth:900,minHeight:600,frame:false,autoHideMenuBar:true,icon:path.join(here,"../../assets/icon.png"),show:!process.env.SVP_SCREENSHOT_PATH,backgroundColor:"#08111f",webPreferences:{preload:path.join(here,"../preload/index.cjs"),contextIsolation:true,nodeIntegration:false,sandbox:true}});
  if(process.env.VITE_DEV_SERVER_URL)await win.loadURL(process.env.VITE_DEV_SERVER_URL);else await win.loadFile(path.join(here,"../../dist/index.html"));
  if(!process.env.SVP_SCREENSHOT_PATH)return;
  await new Promise(resolve=>setTimeout(resolve,4000));
  let downloadStatus:string|undefined;
  if(process.env.SVP_UI_DOWNLOAD_SMOKE_URL&&process.env.SVP_UI_DOWNLOAD_SMOKE_DIR){
    downloadStatus=await win.webContents.executeJavaScript(`(async()=>{const waitFor=async selector=>{for(let i=0;i<480;i++){const found=document.querySelector(selector);if(found)return found;await new Promise(r=>setTimeout(r,125));}throw new Error('UI smoke timeout: '+selector)};const targetDir=${JSON.stringify(process.env.SVP_UI_DOWNLOAD_SMOKE_DIR)};await window.superVideo.invoke('jobs:clear-terminal',{});await window.superVideo.invoke('settings:update',{downloadDir:targetDir});await new Promise(r=>setTimeout(r,1800));const input=await waitFor('input[type=url]');const setter=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;setter.call(input,${JSON.stringify(process.env.SVP_UI_DOWNLOAD_SMOKE_URL)});input.dispatchEvent(new Event('input',{bubbles:true}));document.querySelector('.primary-download').click();await waitFor('.media-choice');document.querySelector('.primary-download').click();for(let i=0;i<480;i++){const job=[...document.querySelectorAll('.job')].find(item=>item.textContent.includes(targetDir));const status=job?.querySelector('.status.completed');if(status)return status.className;await new Promise(r=>setTimeout(r,125));}throw new Error('UI smoke timeout: target completed')})()`);
    await new Promise(resolve=>setTimeout(resolve,750));
  }
  const debug=await win.webContents.executeJavaScript(`(async()=>({location:location.href,html:document.body.innerHTML,bridge:typeof window.superVideo,ready:document.readyState,update:await window.superVideo.invoke('updates:check',{})}))()`);
  await fs.writeFile(`${process.env.SVP_SCREENSHOT_PATH}.json`,JSON.stringify({...debug,downloadStatus},null,2));
  const image=await win.webContents.capturePage();await fs.writeFile(process.env.SVP_SCREENSHOT_PATH,image.toPNG());app.quit();
}

app.whenReady().then(async()=>{
  if(process.env.SVP_BROWSER_SMOKE_OUTPUT){try{await runBrowserSmoke(process.env.SVP_BROWSER_SMOKE_OUTPUT);app.quit();}catch(error){await fs.writeFile(process.env.SVP_BROWSER_SMOKE_OUTPUT,JSON.stringify({error:error instanceof Error?error.stack:String(error)},null,2));app.exit(1);}return;}
  process.env.SVP_TOOL_DIR=path.join(app.getPath("userData"),"tools");
  if(!process.env.SVP_UPDATE_ED25519_PUBLIC_KEY_PEM)process.env.SVP_UPDATE_ED25519_PUBLIC_KEY_PEM=await fs.readFile(path.join(app.getAppPath(),"assets","update-public.pem"),"utf8");
  db=new AppDatabase(app.getPath("userData"));const jobs=new JobManager(db);const diagnostics=new Diagnostics(path.join(app.getPath("userData"),"logs"),jobs.settings().logRetentionDays);diagnostics.write("info","app.start",{version:app.getVersion(),platform:process.platform});
  const updater=new AppUpdater(app.getVersion());const notified=new Set<string>();const loggedState=new Map<string,string>();
  jobs.on("changed",job=>{for(const window of BrowserWindow.getAllWindows())window.webContents.send("jobs:changed",job);const signature=`${job.status}:${Math.floor(job.progress*10)}`;if(loggedState.get(job.id)!==signature){loggedState.set(job.id,signature);diagnostics.write("info","job.changed",{id:job.id,status:job.status,progress:Math.round(job.progress*100),error:job.error});}if(["completed","failed"].includes(job.status)&&!notified.has(`${job.id}:${job.status}`)){notified.add(`${job.id}:${job.status}`);if(Notification.isSupported())new Notification({title:job.status==="completed"?"Download completed":"Download failed",body:job.resource?.title??job.sourceUrl,silent:false}).show();}});
  registerIpc(jobs,diagnostics,updater,new ProductEvidence(db));await createWindow();app.on("activate",()=>{if(BrowserWindow.getAllWindows().length===0)void createWindow();});
});
app.on("window-all-closed",()=>{if(!process.env.SVP_BROWSER_SMOKE_OUTPUT&&process.platform!=="darwin")app.quit();});
app.on("before-quit",()=>db?.close());
