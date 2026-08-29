from __future__ import annotations
from pathlib import Path
from .project import ProjectManager
from .config import load_config
from .doctor import collect_status
from .qa import QACoordinator
from .final_assembler import FinalAssembler
import json
import threading, uuid
from datetime import datetime, timezone
from .persistence import atomic_write_text
from .ingestion import IngestionCoordinator
from .storyboards import StoryboardCoordinator
from newsvid_brain import OllamaConfig, OllamaProvider, NewsStyle, TransitionConfig
from .facts import FactsCoordinator
from .scripts import ScriptCoordinator
from .tts import TTSCoordinator
from newsvid_brain import PiperConfig, PiperProvider, load_pronunciation
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

def create_app(projects_dir: Path | None = None, overrides: dict[str, object] | None = None):
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import FileResponse, PlainTextResponse
    from fastapi.middleware.cors import CORSMiddleware
    config = load_config(); manager = ProjectManager(projects_dir or config.projects_dir); overrides = overrides or {}
    app = FastAPI(title="NewsVid API", version="0.15.0")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    @app.get("/health")
    def health(): return {"status": "ok", "service": "newsvid"}
    jobs: dict[str, dict] = {}
    jobs_lock = threading.RLock()
    def run_job(project_id: str, operation: str, task):
        job_id = str(uuid.uuid4()); now = datetime.now(timezone.utc).isoformat()
        with jobs_lock:
            jobs[job_id] = {"job_id": job_id, "project_id": project_id, "operation": operation, "status": "queued", "progress": 0, "current_stage": "queued", "message": "Queued", "error": None, "created_at": now, "started_at": None, "completed_at": None}
        def worker():
            with jobs_lock:
                jobs[job_id].update(status="running", progress=0.05, current_stage=f"{operation}:execute", started_at=datetime.now(timezone.utc).isoformat(), message="Executing pipeline coordinator")
            try:
                result = task()
                with jobs_lock:
                    jobs[job_id].update(progress=0.95, current_stage=f"{operation}:verify", message="Verifying persisted output")
                # Coordinators return only after schema/media validation and atomic persistence.
                with jobs_lock:
                    jobs[job_id]["result"] = result
                    jobs[job_id].update(status="completed", progress=1, current_stage=f"{operation}:complete", message="Completed and verified", completed_at=datetime.now(timezone.utc).isoformat())
            except Exception as exc:
                with jobs_lock:
                    jobs[job_id].update(status="failed", error=f"{type(exc).__name__}: {exc}", message="Failed", completed_at=datetime.now(timezone.utc).isoformat())
        threading.Thread(target=worker, daemon=True).start()
        with jobs_lock: return dict(jobs[job_id])
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
            return {"exists": exists, "stale": exists and checkpoint.stages[stage].status is not StageStatus.COMPLETED, "size": path.stat().st_size if exists else 0, "modified_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat() if exists else None, "media_url": f"/projects/{project_id}/media/{name}" if exists else None}
        return {"preview": describe("preview.mp4", PipelineStage.PREVIEW), "final": describe("final.mp4", PipelineStage.FINAL_RENDER)}
    @app.get("/projects/{project_id}/media/{name}")
    def media(project_id: str, name: str):
        manager.load(project_id)
        if name not in {"preview.mp4", "final.mp4"}: raise HTTPException(404, "Unknown media output")
        path = manager.project_dir(project_id) / "output" / name
        if not path.is_file(): raise HTTPException(404, "Media output is unavailable")
        return FileResponse(path, media_type="video/mp4", filename=name)
    @app.get("/services/status")
    def services(): return [s.__dict__ for s in collect_status(config)]
    @app.get("/jobs/{job_id}")
    def job(job_id: str):
        with jobs_lock:
            if job_id not in jobs: raise HTTPException(404, "Job not found")
            return dict(jobs[job_id])
    @app.get("/projects/{project_id}/jobs")
    def project_jobs(project_id: str):
        with jobs_lock: return [dict(j) for j in jobs.values() if j["project_id"] == project_id]
    @app.post("/projects/{project_id}/{operation}")
    def operation(project_id: str, operation: str, body: dict | None = None):
        if operation not in {"ingest", "facts", "script", "storyboard", "tts", "align", "visual", "scene", "preview", "render", "validate"}: raise HTTPException(404, "Unknown operation")
        manager.load(project_id)
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
            return run_job(project_id, operation, lambda: ScriptCoordinator(manager, provider).generate(project_id, target_duration=duration, style=style).model_dump(mode="json"))
        if operation == "tts":
            voice = config.services.tts_voice
            tts = overrides.get("tts") or PiperProvider(PiperConfig(executable=config.services.piper_executable, model_path=config.services.piper_model_path, voice_name=voice, speed=config.services.tts_speed, timeout_seconds=config.services.tts_timeout_seconds))
            def generate_tts_chain():
                audio = TTSCoordinator(manager, tts, load_pronunciation(config.pronunciation_path), voice=voice).generate(project_id)
                aligner = overrides.get("alignment") or WhisperXProvider(WhisperXConfig(base_url=config.services.whisperx_url, model=config.services.whisperx_model, timeout_seconds=config.services.whisperx_timeout_seconds))
                layout = SubtitleLayout(top_safe_px=config.services.subtitle_top_safe_px, bottom_safe_px=config.services.subtitle_bottom_safe_px, max_words_per_line=config.services.subtitle_max_words_per_line)
                words, report = AlignmentCoordinator(manager, aligner, layout).generate(project_id)
                return {"audio": audio.model_dump(mode="json"), "words": words.model_dump(mode="json"), "captions": report.model_dump(mode="json")}
            return run_job(project_id, operation, generate_tts_chain)
        if operation == "align":
            aligner = overrides.get("alignment") or WhisperXProvider(WhisperXConfig(base_url=config.services.whisperx_url, model=config.services.whisperx_model, timeout_seconds=config.services.whisperx_timeout_seconds))
            layout = SubtitleLayout(top_safe_px=config.services.subtitle_top_safe_px, bottom_safe_px=config.services.subtitle_bottom_safe_px, max_words_per_line=config.services.subtitle_max_words_per_line)
            return run_job(project_id, operation, lambda: {"words": AlignmentCoordinator(manager, aligner, layout).generate(project_id)[0].model_dump(mode="json")})
        if operation == "visual":
            visual = overrides.get("visual") or HTTPComfyUIProvider(base_url=config.services.comfyui_url, checkpoint=config.services.comfyui_checkpoint, workflow_dir=config.services.comfyui_workflow_dir, timeout_seconds=config.services.comfyui_timeout_seconds, poll_interval_seconds=config.services.comfyui_poll_interval_seconds)
            def generate_visuals():
                manifest = VisualCoordinator(manager, visual).generate(project_id)
                if manifest.failures:
                    details = "; ".join(f"{failure.scene_id}: {failure.error}" for failure in manifest.failures)
                    raise RuntimeError(f"Visual generation failed: {details}")
                return manifest.model_dump(mode="json")
            return run_job(project_id, operation, generate_visuals)
        if operation in {"preview", "render"}:
            root = Path(__file__).resolve().parents[4]
            renderer = VideoRenderCoordinator(manager, ArticleImageCache(max_bytes=config.services.image_max_bytes), SceneRenderer(FFmpegArticleRenderer(ffmpeg=config.services.ffmpeg_executable, ffprobe=config.services.ffprobe_executable), HyperFramesChromiumRenderer(repository_root=root, node=config.services.node_executable, ffmpeg=config.services.ffmpeg_executable, chromium=config.services.chromium_executable)), FinalAssembler(ffmpeg=config.services.ffmpeg_executable, ffprobe=config.services.ffprobe_executable))
            transition = TransitionConfig()
            return run_job(project_id, operation, lambda: (renderer.preview(project_id, transition=transition) if operation == "preview" else renderer.render(project_id, transition=transition)).model_dump(mode="json"))
        if operation == "scene":
            root = Path(__file__).resolve().parents[4]
            renderer = VideoRenderCoordinator(manager, ArticleImageCache(max_bytes=config.services.image_max_bytes), SceneRenderer(FFmpegArticleRenderer(ffmpeg=config.services.ffmpeg_executable, ffprobe=config.services.ffprobe_executable), HyperFramesChromiumRenderer(repository_root=root, node=config.services.node_executable, ffmpeg=config.services.ffmpeg_executable, chromium=config.services.chromium_executable)), FinalAssembler(ffmpeg=config.services.ffmpeg_executable, ffprobe=config.services.ffprobe_executable))
            return run_job(project_id, operation, lambda: renderer.render_scene(project_id, selected_scene_id).model_dump(mode="json"))
        raise HTTPException(400, f"Unsupported operation: {operation}")
    return app
