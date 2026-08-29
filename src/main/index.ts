import { app, BrowserWindow, Notification } from "electron";
import fs from "node:fs/promises";
import {existsSync} from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { AppUpdater } from "./app-updater.js";
import { runBrowserSmoke } from "./browser-smoke.js";
import { AppDatabase } from "./db.js";
import { Diagnostics } from "./diagnostics.js";
import { registerIpc } from "./ipc.js";
import { JobManager } from "./jobs.js";
import {ProductEvidence} from "./product-evidence.js";
import {CompositionManager} from "./composition.js";
import {BackendLifecycle} from "./backend-lifecycle.js";

const here=path.dirname(fileURLToPath(import.meta.url));
let db:AppDatabase|undefined;
let backend:BackendLifecycle|undefined;
let signalShutdown=false;
if(process.env.SVP_UI_AUDIT_PROFILE)app.setPath("userData",process.env.SVP_UI_AUDIT_PROFILE);

async function shutdownFromSignal(){
  if(signalShutdown)return;
  signalShutdown=true;
  await backend?.stop();
  app.quit();
}
process.once("SIGINT",()=>{void shutdownFromSignal();});
process.once("SIGTERM",()=>{void shutdownFromSignal();});

async function createWindow(){
  const win=new BrowserWindow({width:Number(process.env.SVP_SCREENSHOT_WIDTH??1180),height:Number(process.env.SVP_SCREENSHOT_HEIGHT??760),minWidth:900,minHeight:600,frame:false,autoHideMenuBar:true,icon:path.join(here,"../../assets/icon.png"),show:!process.env.SVP_SCREENSHOT_PATH,backgroundColor:"#08111f",webPreferences:{preload:path.join(here,"../preload/index.cjs"),contextIsolation:true,nodeIntegration:false,sandbox:true}});
  const rendererEvents:string[]=[];win.webContents.on("console-message",(_event,level,message)=>{if(level>=3)rendererEvents.push(`console:${level}:${message}`);});win.webContents.on("render-process-gone",(_event,details)=>rendererEvents.push(`gone:${details.reason}:${details.exitCode}`));win.on("unresponsive",()=>rendererEvents.push("window:unresponsive"));
  if(process.env.VITE_DEV_SERVER_URL)await win.loadURL(process.env.VITE_DEV_SERVER_URL);else await win.loadFile(path.join(here,"../../dist/index.html"));
  if(!process.env.SVP_SCREENSHOT_PATH)return;
  await new Promise(resolve=>setTimeout(resolve,4000));
  let downloadStatus:string|undefined;
  if(process.env.SVP_UI_DOWNLOAD_SMOKE_URL&&process.env.SVP_UI_DOWNLOAD_SMOKE_DIR){
    downloadStatus=await win.webContents.executeJavaScript(`(async()=>{const waitFor=async selector=>{for(let i=0;i<480;i++){const found=document.querySelector(selector);if(found)return found;await new Promise(r=>setTimeout(r,125));}throw new Error('UI smoke timeout: '+selector)};const targetDir=${JSON.stringify(process.env.SVP_UI_DOWNLOAD_SMOKE_DIR)};await window.superVideo.invoke('jobs:clear-terminal',{});await window.superVideo.invoke('settings:update',{downloadDir:targetDir});await new Promise(r=>setTimeout(r,1800));const input=await waitFor('input[type=url]');const setter=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;setter.call(input,${JSON.stringify(process.env.SVP_UI_DOWNLOAD_SMOKE_URL)});input.dispatchEvent(new Event('input',{bubbles:true}));document.querySelector('.primary-download').click();await waitFor('.media-choice');document.querySelector('.primary-download').click();for(let i=0;i<480;i++){const response=await window.superVideo.invoke('jobs:list',{limit:200});const jobs=response?.ok?response.data:response;const job=Array.isArray(jobs)?jobs.find(item=>item.destinationDir===targetDir):undefined;if(job?.status==='completed'){const tasks=document.querySelector('[data-tab="tasks"]');if(tasks instanceof HTMLButtonElement)tasks.click();return 'status completed';}if(job?.status==='failed')throw new Error('UI smoke download failed');await new Promise(r=>setTimeout(r,125));}throw new Error('UI smoke timeout: target completed')})()`);
    await new Promise(resolve=>setTimeout(resolve,750));
  }
  if(process.env.SVP_SCREENSHOT_TAB){win.showInactive();await win.webContents.executeJavaScript(`(()=>{const tab=document.querySelector('[data-tab="${process.env.SVP_SCREENSHOT_TAB}"]');if(!(tab instanceof HTMLButtonElement))throw new Error('Screenshot tab not found');tab.click()})()`);await new Promise(resolve=>setTimeout(resolve,1000));}
  if(process.env.SVP_SCREENSHOT_SURFACE){win.showInactive();await win.webContents.executeJavaScript(`(()=>{const trigger=document.querySelector('[data-surface="${process.env.SVP_SCREENSHOT_SURFACE}"]');if(!(trigger instanceof HTMLButtonElement))throw new Error('Screenshot surface trigger not found');trigger.click()})()`);await new Promise(resolve=>setTimeout(resolve,800));}
  let editorPlaybackStatus:string|undefined;
  if(process.env.SVP_SCREENSHOT_PROJECT){const project=await fs.readFile(process.env.SVP_SCREENSHOT_PROJECT,"utf8");editorPlaybackStatus=await win.webContents.executeJavaScript(`(async()=>{window.__svpPlaybackErrors=[];window.addEventListener('error',event=>window.__svpPlaybackErrors.push(event.error?.stack??event.message));window.addEventListener('unhandledrejection',event=>window.__svpPlaybackErrors.push(event.reason?.stack??String(event.reason)));localStorage.setItem('supercut-project-v1',${JSON.stringify(project)});const buttons=[...document.querySelectorAll('button')];const open=buttons.find(item=>item.textContent?.trim()==='Mở');if(!(open instanceof HTMLButtonElement))throw new Error('Project open button not found');open.click();await new Promise(r=>setTimeout(r,1200));const video=document.querySelector('.preview-canvas video');if(!(video instanceof HTMLVideoElement))throw new Error('Preview video not found after project load');const play=[...document.querySelectorAll('.transport button')].find(item=>item.textContent?.includes('▶ /'));if(!(play instanceof HTMLButtonElement))throw new Error('Transport play button not found');play.click();await new Promise(r=>setTimeout(r,${Number(process.env.SVP_SCREENSHOT_PLAY_MS??2500)}));return JSON.stringify({status:'played',currentTime:video.currentTime,paused:video.paused,rootChildren:document.getElementById('root')?.childElementCount??0,bodyText:document.body.innerText.slice(0,300),timeline:Boolean(document.querySelector('.professional-timeline .timeline-editor')),errors:window.__svpPlaybackErrors})})()`);}
  const debug=await win.webContents.executeJavaScript(`(async()=>{let update;try{update=await window.superVideo.invoke('updates:check',{})}catch(error){update={state:'error',message:error instanceof Error?error.message:String(error)}}const selected=[...document.querySelectorAll('[data-tab]')].find(tab=>tab.getAttribute('aria-selected')==='true');return{location:location.href,html:document.body.innerHTML,bridge:typeof window.superVideo,ready:document.readyState,selectedTab:selected?.getAttribute('data-tab'),selectedTabBackground:selected?getComputedStyle(selected).backgroundColor:null,update}})()`);
  const uiAudit=process.env.SVP_UI_AUDIT?await win.webContents.executeJavaScript(`(()=>{const visible=element=>{const style=getComputedStyle(element),rect=element.getBoundingClientRect();return style.visibility!=='hidden'&&style.display!=='none'&&rect.width>0&&rect.height>0};const auditRoot=document.querySelector('[data-open-surface]')??document;const controls=[...auditRoot.querySelectorAll('button,input,select,textarea,[role=button],[role=tab]')].filter(visible);const unlabeled=controls.filter(element=>{const id=element.id,tag=element.tagName.toLowerCase(),text=(element.textContent||'').trim();return !text&&!element.getAttribute('aria-label')&&!element.getAttribute('title')&&!element.closest('label')&&!(id&&document.querySelector('label[for="'+CSS.escape(id)+'"]'))&&tag!=='select'}).map(element=>element.outerHTML.slice(0,180));const smallTargets=controls.filter(element=>{const rect=element.getBoundingClientRect();return !(element instanceof HTMLInputElement&&element.type==='range')&&(rect.width<32||rect.height<32)}).map(element=>{const rect=element.getBoundingClientRect();return{tag:element.tagName,label:element.getAttribute('aria-label')||element.getAttribute('title')||(element.textContent||'').trim().slice(0,40),width:Math.round(rect.width),height:Math.round(rect.height)}});const overflow=[...auditRoot.querySelectorAll('*')].filter(visible).filter(element=>{const rect=element.getBoundingClientRect();return rect.left<-.5||rect.right>innerWidth+.5}).slice(0,30).map(element=>({tag:element.tagName,className:String(element.className).slice(0,80),left:Math.round(element.getBoundingClientRect().left),right:Math.round(element.getBoundingClientRect().right)}));const tabs=[...document.querySelectorAll('[role=tab]')];return{viewport:{width:innerWidth,height:innerHeight},controls:controls.length,unlabeled,smallTargets,overflow,tabSemantics:{count:tabs.length,selected:tabs.filter(tab=>tab.getAttribute('aria-selected')==='true').length,roving:tabs.filter(tab=>tab.getAttribute('tabindex')==='0').length},bodyScroll:{width:document.documentElement.scrollWidth,height:document.documentElement.scrollHeight}}})()`):undefined;
  await fs.writeFile(`${process.env.SVP_SCREENSHOT_PATH}.json`,JSON.stringify({...debug,downloadStatus,editorPlaybackStatus,rendererEvents,uiAudit},null,2));
  const image=await win.webContents.capturePage();await fs.writeFile(process.env.SVP_SCREENSHOT_PATH,image.toPNG());app.quit();
}

app.whenReady().then(async()=>{
  if(process.env.SVP_BROWSER_SMOKE_OUTPUT){try{await runBrowserSmoke(process.env.SVP_BROWSER_SMOKE_OUTPUT);app.quit();}catch(error){await fs.writeFile(process.env.SVP_BROWSER_SMOKE_OUTPUT,JSON.stringify({error:error instanceof Error?error.stack:String(error)},null,2));app.exit(1);}return;}
  process.env.SVP_TOOL_DIR=path.join(app.getPath("userData"),"tools");
  const repositoryRoot=path.join(here,"../.."),venvPython=path.join(repositoryRoot,".venv","Scripts","python.exe");
  if(!process.env.NEWSVID_PYTHON&&existsSync(venvPython))process.env.NEWSVID_PYTHON=venvPython;
  const packagedBackend=path.join(process.resourcesPath,"backend","newsvid-backend","newsvid-backend.exe");
  const backendCommand=process.env.NEWSVID_PYTHON??(app.isPackaged&&existsSync(packagedBackend)?packagedBackend:"python");
  process.env.NEWSVID_PROJECTS_DIR=process.env.NEWSVID_PROJECTS_DIR??path.join(app.getPath("userData"),"newsvid-projects");
  process.env.NEWSVID_FFMPEG=process.env.NEWSVID_FFMPEG??path.join(process.env.SVP_TOOL_DIR,"ffmpeg.exe");
  process.env.NEWSVID_FFPROBE=process.env.NEWSVID_FFPROBE??path.join(process.env.SVP_TOOL_DIR,"ffprobe.exe");
  process.env.NEWSVID_NODE=process.env.NEWSVID_NODE??process.execPath;
  process.env.NEWSVID_NODE_ROOT=process.env.NEWSVID_NODE_ROOT??app.getAppPath();
  backend=new BackendLifecycle({url:process.env.NEWSVID_API_URL??"http://127.0.0.1:8787",command:backendCommand,args:backendCommand===packagedBackend?[]:undefined,cwd:app.isPackaged?process.resourcesPath:repositoryRoot});
  try{await backend.start();}catch(error){console.error("NewsVid backend startup failed",error);app.quit();return;}
  if(!process.env.SVP_UPDATE_ED25519_PUBLIC_KEY_PEM)process.env.SVP_UPDATE_ED25519_PUBLIC_KEY_PEM=await fs.readFile(path.join(app.getAppPath(),"assets","update-public.pem"),"utf8");
  db=new AppDatabase(app.getPath("userData"));const jobs=new JobManager(db);const diagnostics=new Diagnostics(path.join(app.getPath("userData"),"logs"),jobs.settings().logRetentionDays);diagnostics.write("info","app.start",{version:app.getVersion(),platform:process.platform});
  const evidence=new ProductEvidence(db);const compositions=new CompositionManager(db,evidence,()=>jobs.settings().collectProductEvidence,()=>jobs.settings().historyRetentionDays);const updater=new AppUpdater(app.getVersion());const notified=new Set<string>();const loggedState=new Map<string,string>();
  jobs.on("changed",job=>{for(const window of BrowserWindow.getAllWindows())window.webContents.send("jobs:changed",job);const signature=`${job.status}:${Math.floor(job.progress*10)}`;if(loggedState.get(job.id)!==signature){loggedState.set(job.id,signature);diagnostics.write("info","job.changed",{id:job.id,status:job.status,progress:Math.round(job.progress*100),error:job.error});}if(["completed","failed"].includes(job.status)&&!notified.has(`${job.id}:${job.status}`)){notified.add(`${job.id}:${job.status}`);if(Notification.isSupported())new Notification({title:job.status==="completed"?"Download completed":"Download failed",body:job.resource?.title??job.sourceUrl,silent:false}).show();}});
  compositions.on("changed",job=>{for(const window of BrowserWindow.getAllWindows())window.webContents.send("compositions:changed",job);diagnostics.write("info","composition.changed",{id:job.id,status:job.status,progress:Math.round(job.progress*100),error:job.error});});
  registerIpc(jobs,diagnostics,updater,evidence,compositions);await createWindow();app.on("activate",()=>{if(BrowserWindow.getAllWindows().length===0)void createWindow();});
});
app.on("window-all-closed",()=>{if(!process.env.SVP_BROWSER_SMOKE_OUTPUT&&process.platform!=="darwin")app.quit();});
app.on("before-quit",()=>{void backend?.stop();db?.close();});
