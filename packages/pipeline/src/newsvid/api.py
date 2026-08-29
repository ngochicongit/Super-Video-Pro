from __future__ import annotations
from pathlib import Path
from .project import ProjectManager
from .config import load_config
from .doctor import PreflightEngine, TASK_DEPENDENCIES, collect_status
from .qa import QACoordinator
from .final_assembler import FinalAssembler
import json
import httpx
import threading, uuid
from datetime import datetime, timezone
from .persistence import atomic_write_text
from .ingestion import IngestionCoordinator
from .storyboards import StoryboardCoordinator
from newsvid_brain import OllamaConfig, OllamaProvider, NewsStyle, TransitionConfig
from .facts import FactsCoordinator
from .scripts import ScriptCoordinator
from .tts import TTSCoordinator
from newsvid_brain import (F5TTSConfig, F5TTSProvider, PiperConfig, PiperProvider,
                           load_pronunciation)
from .article_renderer import ArticleImageCache, FFmpegArticleRenderer
from .motion_renderer import HyperFramesChromiumRenderer, SceneRenderer
from .video_renderer import VideoRenderCoordinator
from .comfyui import HTTPComfyUIProvider
from .visuals import VisualCoordinator
from .persistence import load_model
from newsvid_brain import Storyboard, FactSet
from .checkpoint import CheckpointStore
from .schemas import PipelineStage, StageStatus
from .alignment import AlignmentCoordinator
from newsvid_brain import WhisperXConfig, WhisperXProvider, SubtitleLayout
from .ollama_setup import OllamaSetupCoordinator, save_service_settings
from .piper_setup import ensure_piper_voice

def create_app(projects_dir: Path | None = None, overrides: dict[str, object] | None = None):
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import FileResponse, PlainTextResponse
    from fastapi.middleware.cors import CORSMiddleware
    config = load_config(); manager = ProjectManager(projects_dir or config.projects_dir); overrides = overrides or {}
    service_settings = manager.root / ".service-settings.json"
    if service_settings.is_file():
        try:
            saved_services = json.loads(service_settings.read_text(encoding="utf-8"))
            for field in ("ollama_model", "tts_provider", "tts_voice", "whisperx_model",
                          "comfyui_checkpoint"):
                if saved_services.get(field) is not None:
                    setattr(config.services, field, saved_services[field])
        except (OSError, ValueError, TypeError):
            pass
    app = FastAPI(title="NewsVid API", version="0.15.0")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    @app.get("/health")
    def health(): return {"status": "ok", "service": "newsvid"}
    jobs: dict[str, dict] = {}
    jobs_lock = threading.RLock()
    preflight = overrides.get("preflight") or PreflightEngine(config)
    def run_job(project_id: str, operation: str, task, *, reports_progress: bool = False,
                skip_preflight: bool = False):
        job_id = str(uuid.uuid4()); now = datetime.now(timezone.utc).isoformat()
        with jobs_lock:
            jobs[job_id] = {"job_id": job_id, "project_id": project_id, "operation": operation, "status": "queued", "progress": 0, "current_stage": "queued", "message": "Đang chờ xử lý", "error": None, "created_at": now, "started_at": None, "completed_at": None}
        def worker():
            with jobs_lock:
                jobs[job_id].update(status="running", progress=0.05, current_stage=f"{operation}:execute", started_at=datetime.now(timezone.utc).isoformat(), message="Đang thực hiện quy trình")
            try:
                def update(progress: float, stage: str, message: str):
                    with jobs_lock:
                        jobs[job_id].update(progress=max(.05, min(.94, progress)),
                                            current_stage=stage, message=message)
                task_name = {"facts":"facts", "script":"script", "storyboard":"storyboard",
                             "tts":"tts", "align":"alignment", "visual":"visual",
                             "scene":"scene", "quick-preview":"scene",
                             "preview":"preview", "render":"render"}.get(operation)
                # Explicit provider overrides are deterministic test/integration boundaries.
                if task_name and not skip_preflight and (not overrides or "preflight" in overrides):
                    preflight.require(task_name, fix=True, progress=lambda value, stage, message:
                                      update(.05 + value * .15, stage, message))
                    update(.21, f"{operation}:execute", "Môi trường đã sẵn sàng")
                result = task(update) if reports_progress else task()
                with jobs_lock:
                    jobs[job_id].update(progress=0.95, current_stage=f"{operation}:verify", message="Đang xác minh kết quả đã lưu")
                # Coordinators return only after schema/media validation and atomic persistence.
                with jobs_lock:
                    jobs[job_id]["result"] = result
                    jobs[job_id].update(status="completed", progress=1, current_stage=f"{operation}:complete", message="Đã hoàn tất và xác minh", completed_at=datetime.now(timezone.utc).isoformat())
            except Exception as exc:
                with jobs_lock:
                    jobs[job_id].update(status="failed", current_stage=f"{operation}:failed",
                                        error=f"{type(exc).__name__}: {exc}",
                                        message="Thực hiện thất bại",
                                        completed_at=datetime.now(timezone.utc).isoformat())
        with jobs_lock:
            initial = dict(jobs[job_id])
        threading.Thread(target=worker, daemon=True).start()
        return initial
    def tts_provider():
        provider = overrides.get("tts")
        if provider is not None:
            return provider
        if config.services.tts_provider == "f5tts":
            return F5TTSProvider(F5TTSConfig(
                base_url=config.services.f5tts_url,
                speed=config.services.tts_speed,
                timeout_seconds=config.services.tts_timeout_seconds,
            ))
        voice = config.services.tts_voice
        ensure_piper_voice(config.services.piper_model_path, voice)
        return PiperProvider(PiperConfig(
            executable=config.services.piper_executable,
            model_path=config.services.piper_model_path,
            voice_name=voice,
            speed=config.services.tts_speed,
            timeout_seconds=config.services.tts_timeout_seconds,
        ))
    def alignment_provider():
        return overrides.get("alignment") or WhisperXProvider(WhisperXConfig(
            base_url=config.services.whisperx_url, model=config.services.whisperx_model,
            timeout_seconds=config.services.whisperx_timeout_seconds,
        ))
    def visual_provider():
        return overrides.get("visual") or HTTPComfyUIProvider(
            base_url=config.services.comfyui_url,
            checkpoint=config.services.comfyui_checkpoint,
            workflow_dir=config.services.comfyui_workflow_dir,
            timeout_seconds=config.services.comfyui_timeout_seconds,
            poll_interval_seconds=config.services.comfyui_poll_interval_seconds,
        )
    def video_renderer():
        root = Path(__file__).resolve().parents[4]
        return VideoRenderCoordinator(
            manager, ArticleImageCache(max_bytes=config.services.image_max_bytes),
            SceneRenderer(
                FFmpegArticleRenderer(ffmpeg=config.services.ffmpeg_executable,
                                      ffprobe=config.services.ffprobe_executable),
                HyperFramesChromiumRenderer(
                    repository_root=root, node=config.services.node_executable,
                    ffmpeg=config.services.ffmpeg_executable,
                    chromium=config.services.chromium_executable,
                ),
            ),
            FinalAssembler(ffmpeg=config.services.ffmpeg_executable,
                           ffprobe=config.services.ffprobe_executable),
        )
    def generate_tts(project_id: str):
        return TTSCoordinator(
            manager, tts_provider(), load_pronunciation(config.pronunciation_path),
            voice=config.services.tts_voice,
        ).generate(project_id)
    def generate_alignment(project_id: str):
        layout = SubtitleLayout(
            top_safe_px=config.services.subtitle_top_safe_px,
            bottom_safe_px=config.services.subtitle_bottom_safe_px,
            max_words_per_line=config.services.subtitle_max_words_per_line,
        )
        return AlignmentCoordinator(manager, alignment_provider(), layout).generate(project_id)
    def generate_visuals(project_id: str, scene_id: str | None = None):
        manifest = VisualCoordinator(manager, visual_provider()).generate(project_id, scene_id=scene_id)
        if manifest.failures:
            details = "; ".join(
                f"{failure.scene_id}: {failure.error}" for failure in manifest.failures
            )
            raise RuntimeError(f"Visual generation failed: {details}")
        return manifest
    @app.get("/projects")
    def projects(): return [p.model_dump(mode="json") for p in manager.list()]
    @app.post("/projects", status_code=201)
    def create(body: dict):
        return manager.create(str(body.get("name", ""))).model_dump(mode="json")
    @app.get("/projects/{project_id}")
    def project(project_id: str):
        try: return manager.load(project_id).model_dump(mode="json")
        except (OSError, ValueError) as exc: raise HTTPException(404, str(exc))
    @app.get("/projects/{project_id}/qa")
    def qa(project_id: str): return QACoordinator(manager, FinalAssembler()).run(project_id)
    @app.get("/projects/{project_id}/storyboard")
    def storyboard(project_id: str):
        try: return json.loads((manager.project_dir(project_id) / "storyboard.json").read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc: raise HTTPException(404, str(exc))
    @app.put("/projects/{project_id}/storyboard")
    def update_storyboard(project_id: str, body: dict):
        manager.load(project_id); project_root = manager.project_dir(project_id)
        try:
            validated = Storyboard.model_validate(body)
            facts = load_model(project_root / "facts.json", FactSet)
            allowed = {fact.id for fact in facts.facts}
            invalid = sorted({ref for scene in validated.scenes for ref in scene.fact_refs if ref not in allowed})
            if invalid: raise ValueError(f"Unknown fact_refs: {', '.join(invalid)}")
        except (OSError, ValueError) as exc: raise HTTPException(422, str(exc))
        try: previous = load_model(project_root / "storyboard.json", Storyboard)
        except (OSError, ValueError): previous = None
        atomic_write_text(project_root / "storyboard.json", validated.model_dump_json(indent=2))
        if previous is not None and previous != validated:
            old = {scene.id: scene for scene in previous.scenes}; new = {scene.id: scene for scene in validated.scenes}
            narration_changed = any(scene_id not in old or old[scene_id].narration != scene.narration for scene_id, scene in new.items()) or set(old) != set(new)
            visual_changed = any(scene_id not in old or old[scene_id].visual != scene.visual or old[scene_id].type != scene.type for scene_id, scene in new.items()) or set(old) != set(new)
            dirty = {PipelineStage.SCENES, PipelineStage.PREVIEW, PipelineStage.QA, PipelineStage.FINAL_RENDER}
            if narration_changed: dirty.update({PipelineStage.TTS, PipelineStage.ALIGNMENT})
            if visual_changed: dirty.add(PipelineStage.VISUALS)
            store = CheckpointStore(project_root / "checkpoint.json")
            for stage in dirty: store.update(stage, StageStatus.PENDING)
        return validated.model_dump(mode="json")
    resource_files = {"source": "source.json", "article": "article.md", "images": "images.json", "facts": "facts.json", "script": "script.json", "storyboard": "storyboard.json", "qa": "qa.json"}
    @app.get("/projects/{project_id}/resources/{resource}")
    def resource(project_id: str, resource: str):
        manager.load(project_id)
        if resource not in resource_files: raise HTTPException(404, "Unknown project resource")
        path = manager.project_dir(project_id) / resource_files[resource]
        if not path.is_file(): raise HTTPException(404, "Resource has not been generated")
        if path.suffix == ".md": return PlainTextResponse(path.read_text(encoding="utf-8"))
        return json.loads(path.read_text(encoding="utf-8"))
    @app.get("/projects/{project_id}/outputs")
    def outputs(project_id: str):
        manager.load(project_id); project_root = manager.project_dir(project_id); root = project_root / "output"
        checkpoint = CheckpointStore(project_root / "checkpoint.json").load()
        def describe(name: str, stage: PipelineStage):
            path = root / name
            exists = path.is_file() and path.stat().st_size > 0
            stage_state = checkpoint.stages[stage]
            expected_output = f"output/{name}"
            stale = exists and (stage_state.status is not StageStatus.COMPLETED
                                or stage_state.metadata.get("output") != expected_output)
            return {"exists": exists, "stale": stale, "size": path.stat().st_size if exists else 0, "modified_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat() if exists else None, "media_url": f"/projects/{project_id}/media/{name}" if exists else None}
        return {"quick_preview": describe("quick-preview.mp4", PipelineStage.PREVIEW),
                "preview": describe("preview.mp4", PipelineStage.PREVIEW),
                "final": describe("final.mp4", PipelineStage.FINAL_RENDER)}
    @app.get("/projects/{project_id}/media/{name}")
    def media(project_id: str, name: str):
        manager.load(project_id)
        if name not in {"quick-preview.mp4", "preview.mp4", "final.mp4"}: raise HTTPException(404, "Unknown media output")
        path = manager.project_dir(project_id) / "output" / name
        if not path.is_file(): raise HTTPException(404, "Media output is unavailable")
        return FileResponse(path, media_type="video/mp4", filename=name)
    @app.get("/services/status")
    def services(): return [s.model_dump(mode="json") for s in collect_status(config)]
    @app.get("/environment/dependencies")
    def environment_dependencies(task: str = "render", fix: bool = False):
        if task not in TASK_DEPENDENCIES: raise HTTPException(422, f"Unknown task: {task}")
        return preflight.run(task, fix=fix).model_dump(mode="json")
    @app.get("/settings/models")
    def model_settings():
        fields = ("ollama_model", "tts_provider", "tts_voice", "whisperx_model", "comfyui_checkpoint")
        return {field: getattr(config.services, field) for field in fields}
    @app.get("/settings/model-options")
    def model_options():
        def unique(values): return list(dict.fromkeys(str(value) for value in values if value))
        ollama = []; whisperx = []; checkpoints = []
        try:
            response = httpx.get(config.services.ollama_url.rstrip("/") + "/api/tags", timeout=2)
            response.raise_for_status(); ollama = [item.get("name") for item in response.json().get("models", [])]
        except Exception: pass
        try:
            response = httpx.get(config.services.whisperx_url.rstrip("/") + "/v1/models", timeout=2)
            response.raise_for_status(); whisperx = [item.get("id") for item in response.json().get("data", [])]
        except Exception: pass
        try:
            response = httpx.get(config.services.comfyui_url.rstrip("/") + "/object_info", timeout=2)
            response.raise_for_status()
            node = response.json().get("CheckpointLoaderSimple", {})
            checkpoints = node.get("input", {}).get("required", {}).get("ckpt_name", [[]])[0]
        except Exception: pass
        installed_voices = [path.stem for path in (Path(__file__).resolve().parents[4] / "models" / "piper").glob("*.onnx")]
        return {
            "ollama_models": unique([*ollama, config.services.ollama_model]),
            "tts_providers": ["piper", "f5tts"],
            "tts_voices": unique([*installed_voices, config.services.tts_voice]),
            "whisperx_models": unique([*whisperx, config.services.whisperx_model]),
            "comfyui_checkpoints": unique([*checkpoints, config.services.comfyui_checkpoint]),
            "availability": {"ollama": bool(ollama), "whisperx": bool(whisperx), "comfyui": bool(checkpoints)},
        }
    @app.put("/settings/models")
    def update_model_settings(body: dict):
        allowed = {"ollama_model", "tts_provider", "tts_voice", "whisperx_model", "comfyui_checkpoint"}
        unknown = set(body) - allowed
        if unknown: raise HTTPException(422, f"Unknown model settings: {', '.join(sorted(unknown))}")
        values = {key: str(value).strip() for key, value in body.items()}
        if any(not value or len(value) > 160 for value in values.values()):
            raise HTTPException(422, "Model setting is empty or too long")
        if "tts_provider" in values and values["tts_provider"] not in {"piper", "f5tts"}:
            raise HTTPException(422, "Unsupported TTS provider")
        for key, value in values.items(): setattr(config.services, key, value)
        save_service_settings(service_settings, **{
            field: getattr(config.services, field) for field in allowed
        })
        return model_settings()
    @app.post("/services/ollama/setup")
    def setup_ollama(body: dict | None = None):
        model = str((body or {}).get("model") or config.services.ollama_setup_model).strip()
        if not model or len(model) > 120 or any(char.isspace() for char in model):
            raise HTTPException(422, "Tên model Ollama không hợp lệ")
        coordinator = overrides.get("ollama_setup") or OllamaSetupCoordinator(config.services.ollama_url)
        def setup(update):
            result = coordinator.setup(model, update)
            config.services.ollama_model = model
            save_service_settings(service_settings, ollama_model=model)
            return result
        return run_job("system", "ollama-setup", setup, reports_progress=True)
    @app.get("/jobs/{job_id}")
    def job(job_id: str):
        with jobs_lock:
            if job_id not in jobs: raise HTTPException(404, "Job not found")
            return dict(jobs[job_id])
    @app.get("/jobs/{job_id}/events")
    def job_events(job_id: str):
        from fastapi.responses import StreamingResponse
        import time
        def stream():
            previous = None
            while True:
                with jobs_lock: current = dict(jobs.get(job_id, {}))
                if not current:
                    yield 'event: error\ndata: {"detail":"Job not found"}\n\n'; return
                encoded = json.dumps(current, ensure_ascii=False, default=str)
                if encoded != previous: yield f"data: {encoded}\n\n"; previous = encoded
                if current.get("status") in {"completed", "failed"}: return
                time.sleep(.25)
        return StreamingResponse(stream(), media_type="text/event-stream")
    @app.get("/projects/{project_id}/jobs")
    def project_jobs(project_id: str):
        with jobs_lock: return [dict(j) for j in jobs.values() if j["project_id"] == project_id]
    @app.post("/projects/{project_id}/{operation}")
    def operation(project_id: str, operation: str, body: dict | None = None):
        if operation not in {"ingest", "facts", "script", "storyboard", "tts", "align", "visual", "scene", "quick-preview", "preview", "render", "validate"}: raise HTTPException(404, "Unknown operation")
        manager.load(project_id)
        CheckpointStore(manager.project_dir(project_id) / "checkpoint.json").reconcile_artifacts(manager.project_dir(project_id))
        selected_scene_id = str((body or {}).get("scene_id", ""))
        if operation in {"tts", "visual", "scene"}:
            if not selected_scene_id: raise HTTPException(422, "scene_id is required")
            try: selected_board = load_model(manager.project_dir(project_id) / "storyboard.json", Storyboard)
            except (OSError, ValueError) as exc: raise HTTPException(422, str(exc))
            if selected_scene_id not in {scene.id for scene in selected_board.scenes}:
                raise HTTPException(422, f"Unknown scene_id: {selected_scene_id}")
        if operation == "validate": return run_job(project_id, operation, lambda: QACoordinator(manager, FinalAssembler()).run(project_id))
        if operation == "ingest":
            source = str((body or {}).get("source", ""))
            if not source: raise HTTPException(422, "source is required")
            def ingest():
                path = Path(source)
                if path.is_file(): return IngestionCoordinator(manager).ingest_file(path, source_url=str((body or {}).get("source_url", "https://fixture.invalid/article")), project_id=project_id).model_dump(mode="json")
                return IngestionCoordinator(manager).ingest_url(source, project_id=project_id).model_dump(mode="json")
            return run_job(project_id, operation, ingest)
        if operation == "storyboard": return run_job(project_id, operation, lambda: StoryboardCoordinator(manager).build(project_id).model_dump(mode="json"))
        provider = overrides.get("llm") or OllamaProvider(OllamaConfig(base_url=config.services.ollama_url, model=config.services.ollama_model, temperature=config.services.ollama_temperature, timeout_seconds=config.services.ollama_timeout_seconds, max_attempts=config.services.ollama_max_attempts))
        if operation == "facts": return run_job(project_id, operation, lambda: FactsCoordinator(manager, provider).extract(project_id).model_dump(mode="json"))
        if operation == "script":
            duration = int((body or {}).get("duration", 60)); style = NewsStyle(str((body or {}).get("style", NewsStyle.BREAKING_NEWS.value)))
            return run_job(
                project_id, operation,
                lambda update: ScriptCoordinator(manager, provider).generate(
                    project_id, target_duration=duration, style=style, progress=update
                ).model_dump(mode="json"),
                reports_progress=True,
            )
        if operation == "tts":
            def generate_tts_job(update):
                update(.12, "tts:tts", "Đang tạo giọng đọc cho các cảnh")
                audio = generate_tts(project_id)
                update(.88, "tts:persist", "Đang xác minh audio đã lưu")
                return {"audio": audio.model_dump(mode="json")}
            return run_job(project_id, operation, generate_tts_job, reports_progress=True)
        if operation == "align":
            return run_job(project_id, operation, lambda: {
                "words": generate_alignment(project_id)[0].model_dump(mode="json")
            })
        if operation == "visual":
            requires_comfyui = any(
                scene.visual.provenance.source_type.value == "generated"
                and scene.visual.provenance.generator == "comfyui"
                for scene in selected_board.scenes if scene.id == selected_scene_id
            )
            return run_job(
                project_id, operation,
                lambda: generate_visuals(project_id, selected_scene_id).model_dump(mode="json"),
                skip_preflight=not requires_comfyui,
            )
        if operation in {"preview", "render"}:
            def render_chain(update):
                update(.10, f"{operation}:tts", "Đang bảo đảm giọng đọc")
                generate_tts(project_id)
                update(.30, f"{operation}:align", "Đang căn chỉnh phụ đề")
                generate_alignment(project_id)
                update(.48, f"{operation}:visuals", "Đang bảo đảm hình ảnh")
                generate_visuals(project_id)
                update(.62, f"{operation}:render", "Đang kết xuất video")
                renderer = video_renderer()
                transition = TransitionConfig()
                result = (renderer.preview(project_id, transition=transition)
                          if operation == "preview"
                          else renderer.render(project_id, transition=transition))
                return result.model_dump(mode="json")
            return run_job(project_id, operation, render_chain, reports_progress=True)
        if operation == "quick-preview":
            def quick_preview_chain(update):
                update(.12, "quick-preview:tts", "Đang bảo đảm giọng đọc")
                generate_tts(project_id)
                update(.38, "quick-preview:visuals", "Đang bảo đảm hình ảnh")
                generate_visuals(project_id)
                update(.62, "quick-preview:render", "Đang kết xuất nhanh không phụ đề")
                return video_renderer().preview(
                    project_id, transition=TransitionConfig(), captions=False
                ).model_dump(mode="json")
            return run_job(project_id, operation, quick_preview_chain, reports_progress=True)
        if operation == "scene":
            def render_scene_chain(update):
                update(.10, "scene:tts", "Đang bảo đảm giọng đọc")
                generate_tts(project_id)
                update(.38, "scene:visuals", "Đang bảo đảm hình ảnh")
                generate_visuals(project_id)
                update(.58, "scene:render", "Đang kết xuất cảnh")
                return video_renderer().render_scene(
                    project_id, selected_scene_id
                ).model_dump(mode="json")
            return run_job(project_id, operation, render_scene_chain, reports_progress=True)
        raise HTTPException(400, f"Unsupported operation: {operation}")
    return app
