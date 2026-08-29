from __future__ import annotations

import importlib.metadata, importlib.util, json, os, platform, re, shutil, subprocess, sys, tempfile, threading, time, wave
from enum import StrEnum
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse
import httpx
from pydantic import BaseModel, ConfigDict, Field
from .config import AppConfig
from .piper_setup import ensure_piper_voice, validate_piper_voice
from .process_env import subprocess_environment
from .whisperx_setup import ensure_whisperx_service

class DependencyKind(StrEnum):
    EXECUTABLE="executable"; PYTHON_PACKAGE="python_package"; NODE_PACKAGE="node_package"; BROWSER="browser"; MODEL="model"; SERVICE="service"; ENVIRONMENT="environment"; CODEC="codec"; FILE="file"
class DependencyState(StrEnum):
    READY="READY"; OPTIONAL_MISSING="OPTIONAL_MISSING"; FIXABLE="FIXABLE"; FIXING="FIXING"; BLOCKED="BLOCKED"; DEGRADED="DEGRADED"; FAILED="FAILED"
class DependencyDefinition(BaseModel):
    model_config=ConfigDict(extra="forbid",frozen=True)
    id:str; display_name:str; kind:DependencyKind; stages:tuple[str,...]; required:bool=True
    minimum_version:str|None=None; capabilities:tuple[str,...]=(); check_method:str; fix_method:str|None=None
    timeout_seconds:float=10; manual_fix:str; platforms:tuple[str,...]=("Windows","Linux","Darwin")
    dependencies:tuple[str,...]=(); cache_ttl_seconds:float=30
class DependencyResult(BaseModel):
    model_config=ConfigDict(extra="forbid")
    id:str; display_name:str; kind:DependencyKind; state:DependencyState; stages:list[str]; required:bool
    check_method:str; detected:str|None=None; location:str|None=None; capabilities:dict[str,bool]=Field(default_factory=dict)
    fixed:list[str]=Field(default_factory=list); missing:list[str]=Field(default_factory=list); manual_fix:str
    root_cause:str|None=None; exit_code:int|None=None; cached:bool=False
class PreflightReport(BaseModel):
    model_config=ConfigDict(extra="forbid")
    schema_version:int=1; task:str; status:DependencyState; platform:str; checked_at:float; fix_requested:bool=False
    results:list[DependencyResult]
    @property
    def ready(self)->bool:return self.status in {DependencyState.READY,DependencyState.DEGRADED}
class PreflightBlockedError(RuntimeError):
    def __init__(self,report:PreflightReport):
        item=next((x for x in report.results if x.required and x.state not in {DependencyState.READY,DependencyState.DEGRADED}),None)
        super().__init__(f"PRECHECK_BLOCKED: {report.task} requires {item.id if item else 'unknown'}; {item.root_cause if item else 'dependency unavailable'}")
        self.report=report

TASK_DEPENDENCIES={
 "facts":("python_runtime","python_packages","ollama"),"script":("python_runtime","python_packages","ollama"),
 "storyboard":("python_runtime","python_packages"),"visual":("python_runtime","python_packages","comfyui"),
 "tts":("python_runtime","python_packages","piper","piper_voice"),
 "alignment":("python_runtime","python_packages","whisperx"),"subtitles":("python_runtime","python_packages","whisperx","subtitle_font"),
 "scene":("python_runtime","python_packages","node","node_packages","lockfile","chromium","ffmpeg","ffprobe","media_capabilities","piper","piper_voice"),
 "preview":("python_runtime","python_packages","node","node_packages","lockfile","chromium","ffmpeg","ffprobe","media_capabilities","piper","piper_voice","whisperx","subtitle_font"),
 "render":("python_runtime","python_packages","node","node_packages","lockfile","chromium","ffmpeg","ffprobe","media_capabilities","piper","piper_voice","whisperx","subtitle_font"),
 "build":("node","pnpm","node_packages","lockfile"),"test":("python_runtime","python_packages","node","pnpm","node_packages","lockfile"),
 "ui-verify":("node","pnpm","node_packages","lockfile","chromium")}

def dependency_registry(c:AppConfig)->dict[str,DependencyDefinition]:
 def d(id,name,kind,stages,check,manual,**kw):return DependencyDefinition(id=id,display_name=name,kind=kind,stages=stages,check_method=check,manual_fix=manual,**kw)
 runtime=tuple(TASK_DEPENDENCIES)
 items=[
 d("python_runtime","Python virtual environment",DependencyKind.ENVIRONMENT,runtime,"sys.executable/version/virtual-prefix","Create .venv with Python 3.11+.",minimum_version="3.11",fix_method="python -m venv .venv"),
 d("python_packages","Python packages",DependencyKind.PYTHON_PACKAGE,runtime,"declared package import metadata","Run active python -m pip install -e .",fix_method="pip install -e .",dependencies=("python_runtime",)),
 d("node","Node.js",DependencyKind.EXECUTABLE,("scene","preview","render","build","test","ui-verify"),"configured executable --version","Install Node.js 20+.",minimum_version="20"),
 d("pnpm","pnpm",DependencyKind.EXECUTABLE,("build","test","ui-verify"),"pnpm --version","Enable Corepack for packageManager version.",minimum_version="11",fix_method="corepack prepare"),
 d("node_packages","Node renderer packages",DependencyKind.NODE_PACKAGE,("scene","preview","render","build","test","ui-verify"),"package manifests under node_modules","Run pnpm install --frozen-lockfile.",fix_method="pnpm install --frozen-lockfile",dependencies=("node",)),
 d("lockfile","Manifest/lockfile synchronization",DependencyKind.FILE,("scene","preview","render","build","test","ui-verify"),"packageManager and pnpm lock importer","Regenerate pnpm-lock.yaml.",fix_method="pnpm install --lockfile-only"),
 d("ffmpeg","FFmpeg",DependencyKind.EXECUTABLE,("scene","preview","render"),"configured FFmpeg -version","Configure NEWSVID_FFMPEG or install FFmpeg 6+.",minimum_version="6"),
 d("ffprobe","FFprobe",DependencyKind.EXECUTABLE,("scene","preview","render"),"configured FFprobe -version","Configure NEWSVID_FFPROBE or install matching FFprobe."),
 d("media_capabilities","Media codecs and filters",DependencyKind.CODEC,("scene","preview","render"),"encoder/filter/format probes plus MP4 smoke","Use full FFmpeg with libx264 and libass.",capabilities=("libx264","libass","scale","overlay","zoompan","xfade","subtitles","concat","aresample","WAV","MP3","WebM","MP4"),dependencies=("ffmpeg","ffprobe"),timeout_seconds=30),
 d("chromium","Chromium renderer",DependencyKind.BROWSER,("scene","preview","render","ui-verify"),"headless local HTML screenshot smoke","Install Playwright Chromium or configure NEWSVID_CHROMIUM.",capabilities=("headless_launch","local_html","screenshot"),fix_method="pnpm exec playwright install chromium",dependencies=("node","node_packages"),timeout_seconds=45),
 d("piper","Piper runtime",DependencyKind.EXECUTABLE,("tts","scene","preview","render"),"configured Piper --help","Install locked piper-tts.",fix_method="pip install piper-tts",dependencies=("python_runtime",)),
 d("piper_voice","Vietnamese Piper voice",DependencyKind.MODEL,("tts","scene","preview","render"),"ONNX/config and UTF-8 WAV smoke","Download configured trusted Piper voice.",capabilities=("onnx_nonempty","json_config","utf8_tts_smoke"),fix_method="official Piper downloader",dependencies=("piper",),timeout_seconds=c.services.tts_timeout_seconds),
 d("f5tts","F5-TTS service",DependencyKind.SERVICE,("tts","scene","preview","render"),"provider health response schema","Start the configured F5-TTS service.",capabilities=("health_schema",)),
 d("whisperx","WhisperX alignment service",DependencyKind.SERVICE,("alignment","subtitles","preview","render"),"health/model response schema","Use automatic setup or start a compatible local WhisperX service.",capabilities=("health_schema","configured_model"),fix_method="isolated WhisperX setup"),
 d("ollama","Ollama LLM",DependencyKind.SERVICE,("facts","script"),"/api/tags schema and configured model","Start Ollama and pull configured model.",capabilities=("configured_model",),fix_method="project Ollama setup"),
 d("comfyui","ComfyUI/SDXL",DependencyKind.SERVICE,("visual",),"/system_stats and /object_info schema","Start ComfyUI and install configured checkpoint.",capabilities=("system_stats","checkpoint")),
 d("subtitle_font","Subtitle font access",DependencyKind.FILE,("subtitles","preview","render"),"readable platform font directory","Install a Vietnamese Unicode TrueType font.")]
 return {x.id:x for x in items}

_locks:dict[str,threading.Lock]={};_locks_guard=threading.Lock()
class PreflightEngine:
 def __init__(self,config:AppConfig,*,repository_root:Path|None=None,runner:Callable[...,subprocess.CompletedProcess[str]]=subprocess.run,transport:httpx.BaseTransport|None=None):
  self.config=config;self.root=(repository_root or Path(__file__).resolve().parents[4]).resolve();self.runner=runner;self.transport=transport;self.registry=dependency_registry(config);self._cache={}
 def run(self,task="render",*,fix=False,strict=False,progress=None)->PreflightReport:
  if task not in TASK_DEPENDENCIES:raise ValueError(f"Unknown preflight task: {task}")
  requested=list(TASK_DEPENDENCIES[task])
  if self.config.services.tts_provider=="f5tts" and task in {"tts","scene","preview","render"}:
   requested=[x for x in requested if x not in {"piper","piper_voice"}]+["f5tts"]
  ids=self._expand(tuple(requested));out=[]
  for i,id in enumerate(ids):
   d=self.registry[id]
   if progress:progress((i+.1)/len(ids),f"preflight:{id}",f"Checking {d.display_name}")
   r=self._probe(d)
   if fix and r.state==DependencyState.FIXABLE:r=self._fix(d,progress)
   out.append(r)
  bad=[x for x in out if x.required and x.state not in {DependencyState.READY,DependencyState.DEGRADED}]
  status=DependencyState.BLOCKED if bad else (DependencyState.DEGRADED if any(x.state==DependencyState.OPTIONAL_MISSING for x in out) else DependencyState.READY)
  report=PreflightReport(task=task,status=status,platform=platform.system(),checked_at=time.time(),fix_requested=fix,results=out)
  if strict and not report.ready:raise PreflightBlockedError(report)
  return report
 def require(self,task,*,fix=True,progress=None):
  report=self.run(task,fix=fix,progress=progress)
  if not report.ready:raise PreflightBlockedError(report)
  return report
 def _expand(self,requested):
  out=[]
  def add(id):
   for child in self.registry[id].dependencies:add(child)
   if id not in out:out.append(id)
  for id in requested:add(id)
  return out
 def _base(self,d,state,**kw):return DependencyResult(id=d.id,display_name=d.display_name,kind=d.kind,state=state,stages=list(d.stages),required=d.required,check_method=d.check_method,manual_fix=d.manual_fix,**kw)
 def _probe(self,d,bypass=False):
  cached=self._cache.get(d.id)
  if not bypass and cached and time.monotonic()-cached[0]<d.cache_ttl_seconds:return cached[1].model_copy(update={"cached":True})
  try:r=getattr(self,"_probe_"+d.id)(d)
  except Exception as e:r=self._base(d,DependencyState.FAILED,root_cause=self._sanitize(str(e)))
  self._cache[d.id]=(time.monotonic(),r);return r
 def _resolve(self,value):
  path=Path(value)
  return str(path.resolve()) if path.is_file() else shutil.which(value)
 def _run(self,args,timeout=10,input=None):return self.runner(args,capture_output=True,text=True,encoding="utf-8",errors="replace",shell=False,timeout=timeout,cwd=self.root,input=input,env=subprocess_environment(str(args[0]) if args else None))
 def _command(self,d,value,args,major=None):
  path=self._resolve(value)
  if not path:return self._base(d,DependencyState.FIXABLE if d.fix_method else DependencyState.BLOCKED,missing=[d.id],root_cause=f"executable not found: {value}")
  r=self._run([path,*args],d.timeout_seconds);text=(r.stdout or r.stderr).strip();m=re.search(r"(\d+)(?:\.\d+)+",text)
  if r.returncode:return self._base(d,DependencyState.FAILED,location=path,root_cause=self._sanitize(text),exit_code=r.returncode)
  if major and m and int(m.group(1))<major:return self._base(d,DependencyState.BLOCKED,detected=m.group(0),location=path,root_cause=f"version below {major}")
  return self._base(d,DependencyState.READY,detected=m.group(0) if m else text[:120],location=path)
 def _probe_python_runtime(self,d):
  state=DependencyState.BLOCKED if sys.version_info<(3,11) else (DependencyState.READY if sys.prefix!=getattr(sys,"base_prefix",sys.prefix) else DependencyState.DEGRADED)
  return self._base(d,state,detected=platform.python_version(),location=sys.executable,root_cause="Python 3.11+ required" if state==DependencyState.BLOCKED else ("running outside a virtual environment" if state==DependencyState.DEGRADED else None))
 def _probe_python_packages(self,d):
  names=("bs4","httpx","pydantic","piper","yaml","trafilatura","fastapi","uvicorn");missing=[x for x in names if importlib.util.find_spec(x) is None]
  return self._base(d,DependencyState.FIXABLE if missing else DependencyState.READY,missing=missing,detected=None if missing else "runtime imports ready",location=sys.prefix,root_cause=("missing packages: "+", ".join(missing)) if missing else None)
 def _probe_node(self,d):return self._command(d,self.config.services.node_executable,["--version"],20)
 def _probe_pnpm(self,d):return self._command(d,"pnpm",["--version"],11)
 def _probe_ffmpeg(self,d):return self._command(d,self.config.services.ffmpeg_executable,["-version"],6)
 def _probe_ffprobe(self,d):return self._command(d,self.config.services.ffprobe_executable,["-version"])
 def _probe_piper(self,d):return self._command(d,self.config.services.piper_executable,["--help"])
 def _probe_node_packages(self,d):
  wanted=("playwright","gsap","react");missing=[x for x in wanted if not (self.root/"node_modules"/x/"package.json").is_file()]
  return self._base(d,DependencyState.FIXABLE if missing else DependencyState.READY,missing=missing,detected="renderer packages ready" if not missing else None,location=str(self.root/"node_modules"),root_cause=("missing Node packages: "+", ".join(missing)) if missing else None)
 def _probe_lockfile(self,d):
  package=self.root/"package.json";lock=self.root/"pnpm-lock.yaml";ok=package.is_file() and lock.is_file() and "importers:" in lock.read_text(encoding="utf-8") and str(json.loads(package.read_text(encoding="utf-8")).get("packageManager","")).startswith("pnpm@")
  return self._base(d,DependencyState.READY if ok else DependencyState.FIXABLE,location=str(lock),root_cause=None if ok else "manifest/lockfile missing or incompatible")
 def _probe_media_capabilities(self,d):
  ff=self._resolve(self.config.services.ffmpeg_executable);probe=self._resolve(self.config.services.ffprobe_executable)
  if not ff or not probe:return self._base(d,DependencyState.BLOCKED,root_cause="FFmpeg toolchain unavailable")
  enc=self._run([ff,"-hide_banner","-encoders"],15).stdout;filters=self._run([ff,"-hide_banner","-filters"],15).stdout;formats=self._run([ff,"-hide_banner","-formats"],15).stdout
  caps={"libx264":"libx264" in enc,"libass":"subtitles" in filters}
  for x in ("scale","overlay","zoompan","xfade","subtitles","concat","aresample"):caps[x]=re.search(rf"\b{x}\b",filters)!=None
  for name,x in (("WAV","wav"),("MP3","mp3"),("WebM","webm"),("MP4","mp4")):caps[name]=re.search(rf"\b{x}\b",formats,re.I)!=None
  missing=[x for x,v in caps.items() if not v]
  if missing:return self._base(d,DependencyState.BLOCKED,location=ff,capabilities=caps,missing=missing,root_cause="missing FFmpeg capabilities: "+", ".join(missing))
  with tempfile.TemporaryDirectory(prefix="newsvid-media-") as td:
   out=Path(td)/"smoke.mp4";r=self._run([ff,"-y","-f","lavfi","-i","color=c=black:s=64x64:d=0.12","-f","lavfi","-i","anullsrc=r=16000:cl=mono","-shortest","-c:v","libx264","-c:a","aac",str(out)],30)
   q=self._run([probe,"-v","error","-show_entries","stream=codec_name","-of","json",str(out)],10) if r.returncode==0 else r
   if r.returncode or q.returncode or not out.is_file() or not out.stat().st_size:return self._base(d,DependencyState.FAILED,location=ff,capabilities=caps,root_cause=self._sanitize((r.stderr or q.stderr)[-500:]),exit_code=r.returncode or q.returncode)
  return self._base(d,DependencyState.READY,detected="capabilities and MP4 smoke passed",location=ff,capabilities=caps)
 def _probe_chromium(self,d):
  browser=self.config.services.chromium_executable
  if not browser.is_file():return self._base(d,DependencyState.FIXABLE,missing=[str(browser)],root_cause="Chromium executable missing")
  node=self._resolve(self.config.services.node_executable)
  js="import {chromium} from'playwright';import fs from'node:fs';import os from'node:os';import path from'node:path';let d=fs.mkdtempSync(path.join(os.tmpdir(),'nv-'));let f=path.join(d,'x.html');fs.writeFileSync(f,'xin chào');let b=await chromium.launch({headless:true,executablePath:process.argv[1]});let p=await b.newPage();await p.goto('file:///'+f.replaceAll('\\\\','/'));await p.screenshot({path:path.join(d,'x.png')});await b.close();fs.rmSync(d,{recursive:true,force:true});"
  r=self._run([node or "node","--input-type=module","-e",js,str(browser)],d.timeout_seconds)
  caps={"headless_launch":r.returncode==0,"local_html":r.returncode==0,"screenshot":r.returncode==0}
  return self._base(d,DependencyState.READY if r.returncode==0 else DependencyState.FAILED,location=str(browser),capabilities=caps,detected="headless local HTML screenshot passed" if r.returncode==0 else None,root_cause=None if r.returncode==0 else self._sanitize(r.stderr[-500:]),exit_code=r.returncode or None)
 def _probe_piper_voice(self,d):
  model=self.config.services.piper_model_path;meta=Path(str(model)+".json")
  if not validate_piper_voice(model,self.config.services.tts_voice):return self._base(d,DependencyState.FIXABLE,location=str(model),root_cause="Piper model/config missing, truncated or checksum mismatch")
  try:json.loads(meta.read_text(encoding="utf-8"))
  except Exception as e:return self._base(d,DependencyState.FIXABLE,location=str(model),root_cause=f"invalid Piper config: {e}")
  piper=self._resolve(self.config.services.piper_executable)
  with tempfile.TemporaryDirectory(prefix="newsvid-tts-") as td:
   wav=Path(td)/"tiếng Việt.wav";r=self._run([piper or "piper","--model",str(model),"--output_file",str(wav)],d.timeout_seconds,input="Xin chào Việt Nam.")
   try:
    with wave.open(str(wav),"rb") as w:duration=w.getnframes()/w.getframerate()
   except Exception:duration=0
   if r.returncode or duration<=0:return self._base(d,DependencyState.FAILED,location=str(model),root_cause=self._sanitize(r.stderr or "invalid WAV"),exit_code=r.returncode)
  return self._base(d,DependencyState.READY,detected=f"{model.stat().st_size} bytes; UTF-8 WAV smoke passed",location=str(model),capabilities={"onnx_nonempty":True,"json_config":True,"utf8_tts_smoke":True})
 def _get(self,url):
  with httpx.Client(timeout=2.5,transport=self.transport) as c:return c.get(url)
 def _service_error(self,d,url,e):
  msg=str(e);cause=("authentication failed" if "401" in msg or "403" in msg else "health check timed out" if "timed out" in msg.lower() else "health check failed")+f" at {self._url(url)}: {msg}"
  return self._base(d,DependencyState.BLOCKED,location=self._url(url),root_cause=self._sanitize(cause))
 def _probe_ollama(self,d):
  url=self.config.services.ollama_url.rstrip("/")
  try:
   r=self._get(url+"/api/tags");r.raise_for_status();items=r.json().get("models");assert isinstance(items,list);names={str(x.get("name","")) for x in items};model=self.config.services.ollama_model
   if model not in names and model.split(":")[0] not in {x.split(":")[0] for x in names}:return self._base(d,DependencyState.FIXABLE,location=url,missing=[model],root_cause=f"configured model unavailable: {model}")
   return self._base(d,DependencyState.READY,detected=model,location=url,capabilities={"configured_model":True})
  except Exception as e:return self._service_error(d,url,e)
 def _probe_whisperx(self,d):
  url=self.config.services.whisperx_url.rstrip("/")
  try:
   health=self._get(url+"/health");health.raise_for_status()
   try:body=health.json()
   except ValueError as exc:raise ValueError("incompatible health response schema") from exc
   if not isinstance(body,dict) or str(body.get("status","")).lower() not in {"ok","healthy","ready"}:raise ValueError("incompatible health response schema")
   models=self._get(url+"/v1/models");models.raise_for_status();payload=models.json();model=self.config.services.whisperx_model
   if not isinstance(payload,dict) or model not in json.dumps(payload):raise ValueError(f"configured model unavailable: {model}")
   return self._base(d,DependencyState.READY,detected=model,location=url,capabilities={"health_schema":True,"configured_model":True})
  except Exception as e:
   result=self._service_error(d,url,e)
   if isinstance(e,(httpx.ConnectError,httpx.ConnectTimeout)) and urlparse(url).hostname in {"127.0.0.1","localhost","::1"}:result.state=DependencyState.FIXABLE
   return result
 def _probe_comfyui(self,d):
  url=self.config.services.comfyui_url.rstrip("/")
  try:
   a=self._get(url+"/system_stats");a.raise_for_status();assert isinstance(a.json(),dict);b=self._get(url+"/object_info");b.raise_for_status();model=self.config.services.comfyui_checkpoint
   if model not in json.dumps(b.json()):return self._base(d,DependencyState.BLOCKED,location=url,missing=[model],root_cause=f"configured checkpoint unavailable: {model}")
   return self._base(d,DependencyState.READY,detected=model,location=url,capabilities={"system_stats":True,"checkpoint":True})
  except Exception as e:return self._service_error(d,url,e)
 def _probe_f5tts(self,d):
  url=self.config.services.f5tts_url.rstrip("/")
  try:
   response=self._get(url+"/health");response.raise_for_status();payload=response.json()
   if not isinstance(payload,dict) or str(payload.get("status","")).lower() not in {"ok","healthy","ready"}:raise ValueError("incompatible health response schema")
   return self._base(d,DependencyState.READY,detected="F5-TTS ready",location=url,capabilities={"health_schema":True})
  except Exception as e:return self._service_error(d,url,e)
 def _probe_subtitle_font(self,d):
  root=(Path(os.environ.get("WINDIR","C:/Windows"))/"Fonts") if platform.system()=="Windows" else (Path("/System/Library/Fonts") if platform.system()=="Darwin" else Path("/usr/share/fonts"));fonts=list(root.rglob("*.ttf"))[:1] if root.is_dir() else []
  return self._base(d,DependencyState.READY if fonts else DependencyState.BLOCKED,detected=fonts[0].name if fonts else None,location=str(root),root_cause=None if fonts else "no readable TrueType font")
 def _fix(self,d,progress):
  with _locks_guard:lock=_locks.setdefault(d.id,threading.Lock())
  with lock:
   current=self._probe(d,True)
   if current.state!=DependencyState.FIXABLE:return current
   if progress:progress(.02,f"preflight:{d.id}:fixing",f"Fixing {d.display_name}")
   try:
    if d.id=="piper_voice":ensure_piper_voice(self.config.services.piper_model_path,self.config.services.tts_voice);fixed=["downloaded trusted Piper voice atomically"]
    elif d.id=="whisperx":fixed=ensure_whisperx_service(self.root,self.config.services.whisperx_url,self.config.services.whisperx_model)
    else:
     commands={"python_packages":[sys.executable,"-m","pip","install","-e","."],"piper":[sys.executable,"-m","pip","install","piper-tts>=1.7,<2"],"node_packages":[self._resolve("pnpm") or "pnpm","install","--frozen-lockfile"],"lockfile":[self._resolve("pnpm") or "pnpm","install","--lockfile-only"],"pnpm":[self._resolve("corepack") or "corepack","prepare","pnpm@11.19.0","--activate"],"chromium":[self._resolve("pnpm") or "pnpm","exec","playwright","install","chromium"]}
     cmd=commands.get(d.id)
     if not cmd:return current
     r=self._run(cmd,600)
     if r.returncode:raise RuntimeError(r.stderr or r.stdout)
     fixed=["completed safe idempotent autofix"]
    return self._probe(d,True).model_copy(update={"fixed":fixed})
   except Exception as e:return current.model_copy(update={"state":DependencyState.FAILED,"root_cause":self._sanitize(str(e))})
 @staticmethod
 def _url(value):return re.sub(r"(?i)([?&](?:key|token|api_key)=)[^&]+",r"\1<redacted>",value)
 @classmethod
 def _sanitize(cls,value):return re.sub(r"(?i)(bearer\s+|api[_-]?key[=:]\s*|token[=:]\s*)[^\s,;]+",r"\1<redacted>",cls._url(str(value)))[:1000]

def collect_status(config:AppConfig)->list[DependencyResult]:
 engine=PreflightEngine(config);return [engine._probe(x) for x in engine.registry.values()]
