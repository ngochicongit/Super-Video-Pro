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

def create_app(projects_dir: Path | None = None):
    from fastapi import FastAPI, HTTPException
    config = load_config(); manager = ProjectManager(projects_dir or config.projects_dir)
    app = FastAPI(title="NewsVid API", version="0.15.0")
    @app.get("/health")
    def health(): return {"status": "ok", "service": "newsvid"}
    jobs: dict[str, dict] = {}
    def run_job(project_id: str, operation: str, task):
        job_id = str(uuid.uuid4()); now = datetime.now(timezone.utc).isoformat(); jobs[job_id] = {"job_id": job_id, "project_id": project_id, "operation": operation, "status": "queued", "progress": 0, "current_stage": operation, "message": "Queued", "error": None, "created_at": now, "started_at": None, "completed_at": None}
        def worker():
            item = jobs[job_id]; item.update(status="running", started_at=datetime.now(timezone.utc).isoformat(), message="Running")
            try: item["result"] = task(); item.update(status="completed", progress=1, message="Completed", completed_at=datetime.now(timezone.utc).isoformat())
            except Exception as exc: item.update(status="failed", error=f"{type(exc).__name__}: {exc}", message="Failed", completed_at=datetime.now(timezone.utc).isoformat())
        threading.Thread(target=worker, daemon=True).start(); return jobs[job_id]
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
        manager.load(project_id)
        if "scenes" not in body or not isinstance(body["scenes"], list): raise HTTPException(422, "storyboard.scenes is required")
        atomic_write_text(manager.project_dir(project_id) / "storyboard.json", json.dumps(body, ensure_ascii=True, indent=2))
        return body
    @app.get("/services/status")
    def services(): return [s.__dict__ for s in collect_status(config)]
    @app.get("/jobs/{job_id}")
    def job(job_id: str):
        if job_id not in jobs: raise HTTPException(404, "Job not found")
        return jobs[job_id]
    @app.get("/projects/{project_id}/jobs")
    def project_jobs(project_id: str): return [j for j in jobs.values() if j["project_id"] == project_id]
    @app.post("/projects/{project_id}/{operation}")
    def operation(project_id: str, operation: str, body: dict | None = None):
        if operation not in {"ingest", "facts", "script", "storyboard", "tts", "visual", "scene", "preview", "render", "validate"}: raise HTTPException(404, "Unknown operation")
        manager.load(project_id)
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
        provider = OllamaProvider(OllamaConfig(base_url=config.services.ollama_url, model=config.services.ollama_model, temperature=config.services.ollama_temperature, timeout_seconds=config.services.ollama_timeout_seconds, max_attempts=config.services.ollama_max_attempts))
        if operation == "facts": return run_job(project_id, operation, lambda: FactsCoordinator(manager, provider).extract(project_id).model_dump(mode="json"))
        if operation == "script":
            duration = int((body or {}).get("duration", 60)); style = NewsStyle(str((body or {}).get("style", NewsStyle.BREAKING_NEWS.value)))
            return run_job(project_id, operation, lambda: ScriptCoordinator(manager, provider).generate(project_id, target_duration=duration, style=style).model_dump(mode="json"))
        if operation == "tts":
            voice = config.services.tts_voice
            tts = PiperProvider(PiperConfig(executable=config.services.piper_executable, model_path=config.services.piper_model_path, voice_name=voice, speed=config.services.tts_speed, timeout_seconds=config.services.tts_timeout_seconds))
            return run_job(project_id, operation, lambda: TTSCoordinator(manager, tts, load_pronunciation(config.pronunciation_path), voice=voice).generate(project_id).model_dump(mode="json"))
        if operation == "visual":
            visual = HTTPComfyUIProvider(base_url=config.services.comfyui_url, checkpoint=config.services.comfyui_checkpoint, workflow_dir=config.services.comfyui_workflow_dir, timeout_seconds=config.services.comfyui_timeout_seconds, poll_interval_seconds=config.services.comfyui_poll_interval_seconds)
            return run_job(project_id, operation, lambda: VisualCoordinator(manager, visual).generate(project_id).model_dump(mode="json"))
        if operation in {"preview", "render"}:
            root = Path(__file__).resolve().parents[4]
            renderer = VideoRenderCoordinator(manager, ArticleImageCache(max_bytes=config.services.image_max_bytes), SceneRenderer(FFmpegArticleRenderer(ffmpeg=config.services.ffmpeg_executable, ffprobe=config.services.ffprobe_executable), HyperFramesChromiumRenderer(repository_root=root, node=config.services.node_executable, ffmpeg=config.services.ffmpeg_executable, chromium=config.services.chromium_executable)), FinalAssembler(ffmpeg=config.services.ffmpeg_executable, ffprobe=config.services.ffprobe_executable))
            transition = TransitionConfig()
            return run_job(project_id, operation, lambda: (renderer.preview(project_id, transition=transition) if operation == "preview" else renderer.render(project_id, transition=transition)).model_dump(mode="json"))
        if operation == "scene":
            scene_id = str((body or {}).get("scene_id", ""))
            if not scene_id: raise HTTPException(422, "scene_id is required")
            root = Path(__file__).resolve().parents[4]
            renderer = VideoRenderCoordinator(manager, ArticleImageCache(max_bytes=config.services.image_max_bytes), SceneRenderer(FFmpegArticleRenderer(ffmpeg=config.services.ffmpeg_executable, ffprobe=config.services.ffprobe_executable), HyperFramesChromiumRenderer(repository_root=root, node=config.services.node_executable, ffmpeg=config.services.ffmpeg_executable, chromium=config.services.chromium_executable)), FinalAssembler(ffmpeg=config.services.ffmpeg_executable, ffprobe=config.services.ffprobe_executable))
            return run_job(project_id, operation, lambda: renderer.render_scene(project_id, scene_id).model_dump(mode="json"))
        raise HTTPException(501, f"Operation {operation} is not wired to a real coordinator yet")
    return app
