from __future__ import annotations
import json, shutil, subprocess, threading, time
from pathlib import Path
import httpx, pytest
from newsvid.checkpoint import CheckpointStore
from newsvid.config import AppConfig
from newsvid.doctor import DependencyState, PreflightEngine, TASK_DEPENDENCIES
from newsvid.schemas import PipelineStage, StageStatus

def config(tmp_path:Path)->AppConfig:
    value=AppConfig(); value.services.piper_model_path=tmp_path/"voice.onnx"
    value.services.chromium_executable=tmp_path/"chromium.exe"; return value
def completed(args,code=0,out="",err=""):
    return subprocess.CompletedProcess(args,code,out,err)
def engine(tmp_path,runner=lambda args,**kw:completed(args,out="version 24.0.0"),transport=None):
    root=tmp_path/"repo";root.mkdir(exist_ok=True);(root/"package.json").write_text('{"packageManager":"pnpm@11.19.0"}')
    (root/"pnpm-lock.yaml").write_text("importers:\n  .: {}\n")
    for name in ("playwright","gsap","react"):
        p=root/"node_modules"/name;p.mkdir(parents=True,exist_ok=True);(p/"package.json").write_text('{"version":"1.0.0"}')
    return PreflightEngine(config(tmp_path),repository_root=root,runner=runner,transport=transport)

def test_task_graph_has_direct_and_transitive_dependencies(tmp_path):
    e=engine(tmp_path); ids=e._expand(TASK_DEPENDENCIES["render"])
    assert ids.index("ffmpeg")<ids.index("media_capabilities");assert {"whisperx","chromium","piper_voice"}<=set(ids)
def test_missing_ffmpeg_reports_root_dependency(tmp_path,monkeypatch):
    e=engine(tmp_path);monkeypatch.setattr(e,"_resolve",lambda value:None)
    r=e._probe_ffmpeg(e.registry["ffmpeg"]);assert r.state==DependencyState.BLOCKED;assert "not found" in r.root_cause
def test_ffmpeg_without_libx264_is_blocked(tmp_path,monkeypatch):
    e=engine(tmp_path);monkeypatch.setattr(e,"_resolve",lambda value:"tool")
    monkeypatch.setattr(e,"_run",lambda args,*a,**k:completed(args,out="scale overlay zoompan xfade subtitles concat aresample wav mp3 webm mp4"))
    r=e._probe_media_capabilities(e.registry["media_capabilities"]);assert "libx264" in r.missing
def test_configured_ffmpeg_outside_path_is_used(tmp_path):
    tool=tmp_path/"Có dấu và khoảng trắng"/"ffmpeg.exe";tool.parent.mkdir();tool.write_bytes(b"x")
    e=engine(tmp_path);e.config.services.ffmpeg_executable=str(tool)
    assert e._probe_ffmpeg(e.registry["ffmpeg"]).location==str(tool.resolve())
def test_missing_chromium_is_fixable(tmp_path):
    e=engine(tmp_path);assert e._probe_chromium(e.registry["chromium"]).state==DependencyState.FIXABLE
def test_chromium_launch_failure_is_failed(tmp_path):
    e=engine(tmp_path,lambda args,**kw:completed(args,9,err="launch failed"));e.config.services.chromium_executable.write_bytes(b"x")
    r=e._probe_chromium(e.registry["chromium"]);assert r.state==DependencyState.FAILED;assert r.exit_code==9
def test_missing_python_package_is_fixable(tmp_path,monkeypatch):
    e=engine(tmp_path);monkeypatch.setattr("newsvid.doctor.importlib.util.find_spec",lambda name:None if name=="fastapi" else object())
    assert "fastapi" in e._probe_python_packages(e.registry["python_packages"]).missing
def test_missing_node_package_is_fixable(tmp_path):
    e=engine(tmp_path);(e.root/"node_modules"/"gsap"/"package.json").unlink()
    assert "gsap" in e._probe_node_packages(e.registry["node_packages"]).missing
def test_piper_missing_and_partial_model_are_fixable(tmp_path):
    e=engine(tmp_path);d=e.registry["piper_voice"];assert e._probe_piper_voice(d).state==DependencyState.FIXABLE
    e.config.services.piper_model_path.write_bytes(b"partial");Path(str(e.config.services.piper_model_path)+".json").write_text("{}")
    assert "truncated" in e._probe_piper_voice(d).root_cause
def test_unicode_tts_uses_utf8_and_valid_wav_path(tmp_path,monkeypatch):
    e=engine(tmp_path);e.config.services.tts_voice="vi_VN-test-medium";model=e.config.services.piper_model_path;model.write_bytes(b"x"*1_000_001);Path(str(model)+".json").write_text("{}")
    monkeypatch.setattr(e,"_resolve",lambda value:"piper")
    def run(args,*a,input=None,**kw):
        import wave
        with wave.open(args[-1],"wb") as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(b"\0\0"*100)
        assert input=="Xin chào Việt Nam.";return completed(args)
    monkeypatch.setattr(e,"_run",run);assert e._probe_piper_voice(e.registry["piper_voice"]).state==DependencyState.READY
def service_engine(tmp_path,handler):return engine(tmp_path,transport=httpx.MockTransport(handler))
def test_whisperx_offline_is_fixable(tmp_path):
    def fail(request):raise httpx.ConnectError("connection refused",request=request)
    r=service_engine(tmp_path,fail)._probe_whisperx(engine(tmp_path).registry["whisperx"]);assert r.state==DependencyState.FIXABLE
def test_whisperx_auth_failure_is_distinguished(tmp_path):
    e=service_engine(tmp_path,lambda r:httpx.Response(401,request=r));result=e._probe_whisperx(e.registry["whisperx"]);assert "authentication failed" in result.root_cause
def test_open_endpoint_without_model_is_blocked(tmp_path):
    e=service_engine(tmp_path,lambda r:httpx.Response(200,json={"data":[{"id":"tiny"}]},request=r));result=e._probe_whisperx(e.registry["whisperx"]);assert result.state==DependencyState.BLOCKED
def test_port_occupied_by_incompatible_process_reports_schema_error(tmp_path):
    e=service_engine(tmp_path,lambda r:httpx.Response(200,text="another service",request=r));result=e._probe_whisperx(e.registry["whisperx"])
    assert result.state==DependencyState.BLOCKED and "response schema" in result.root_cause
def test_optional_dependency_does_not_block(monkeypatch,tmp_path):
    e=engine(tmp_path);d=e.registry["comfyui"].model_copy(update={"required":False});r=e._base(d,DependencyState.OPTIONAL_MISSING)
    assert not r.required and r.state==DependencyState.OPTIONAL_MISSING
def test_manifest_reference_to_empty_file_invalidates_checkpoint(tmp_path):
    store=CheckpointStore(tmp_path/"checkpoint.json");store.initialize("sample");(tmp_path/"audio").mkdir();(tmp_path/"audio"/"tts_manifest.json").write_text(json.dumps({"entries":[{"audio_path":"audio/a.wav"}]}));(tmp_path/"audio"/"a.wav").write_bytes(b"")
    store.update(PipelineStage.TTS,StageStatus.COMPLETED);assert store.reconcile_artifacts(tmp_path).stages[PipelineStage.TTS].status==StageStatus.FAILED
def test_deleted_completed_artifact_is_invalidated(tmp_path):
    store=CheckpointStore(tmp_path/"checkpoint.json");store.initialize("sample");store.update(PipelineStage.FACTS,StageStatus.COMPLETED)
    assert store.reconcile_artifacts(tmp_path).stages[PipelineStage.FACTS].status==StageStatus.FAILED
def test_valid_completed_artifact_is_preserved_on_resume(tmp_path):
    store=CheckpointStore(tmp_path/"checkpoint.json");store.initialize("sample");(tmp_path/"facts.json").write_text("{}") ;store.update(PipelineStage.FACTS,StageStatus.COMPLETED)
    assert store.reconcile_artifacts(tmp_path).stages[PipelineStage.FACTS].status==StageStatus.COMPLETED
def test_two_fixes_are_serialized(tmp_path,monkeypatch):
    e=engine(tmp_path);d=e.registry["piper_voice"];active=0;maximum=0
    monkeypatch.setattr(e,"_probe",lambda definition,bypass=False:e._base(d,DependencyState.FIXABLE))
    def fix(*a,**k):
        nonlocal active,maximum;active+=1;maximum=max(maximum,active);time.sleep(.03);active-=1
    monkeypatch.setattr("newsvid.doctor.ensure_piper_voice",fix)
    threads=[threading.Thread(target=e._fix,args=(d,None)) for _ in range(2)];[x.start() for x in threads];[x.join() for x in threads];assert maximum==1
def test_windows_unicode_path_is_argument_not_shell(tmp_path):
    calls=[]
    def runner(args,**kw):calls.append((args,kw));return completed(args,out="ffmpeg version 6.1")
    e=engine(tmp_path,runner);tool=tmp_path/"Thư mục có dấu"/"ffmpeg.exe";tool.parent.mkdir();tool.write_bytes(b"x");e.config.services.ffmpeg_executable=str(tool);e._probe_ffmpeg(e.registry["ffmpeg"])
    assert calls[0][0][0]==str(tool.resolve()) and calls[0][1]["shell"] is False
def test_electron_executable_is_launched_in_embedded_node_mode(tmp_path):
    calls=[]
    def runner(args,**kwargs):calls.append(kwargs);return completed(args,out="v24.0.0")
    e=engine(tmp_path,runner);electron=tmp_path/"electron.exe";electron.write_bytes(b"x");e.config.services.node_executable=str(electron)
    assert e._probe_node(e.registry["node"]).state==DependencyState.READY
    assert calls[0]["env"]["ELECTRON_RUN_AS_NODE"]=="1"
def test_secrets_are_redacted_from_report(tmp_path):
    value=PreflightEngine._sanitize("https://x.test?a=1&api_key=secret token=hidden Bearer abc")
    assert "secret" not in value and "hidden" not in value and "abc" not in value
def test_render_media_probe_runs_real_clip_and_ffprobe(tmp_path,monkeypatch):
    e=engine(tmp_path,subprocess.run);monkeypatch.setattr(e,"_resolve",lambda value:shutil.which(value))
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):pytest.skip("real FFmpeg unavailable")
    result=e._probe_media_capabilities(e.registry["media_capabilities"]);assert result.state==DependencyState.READY
