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

def create_app(projects_dir: Path | None = None):
    from fastapi import FastAPI, HTTPException
    config = load_config(); manager = ProjectManager(projects_dir or config.projects_dir)
    app = FastAPI(title="NewsVid API", version="0.15.0")
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
    def operation(project_id: str, operation: str):
        if operation not in {"generate", "scene", "preview", "render", "validate"}: raise HTTPException(404, "Unknown operation")
        manager.load(project_id)
        if operation == "validate": return run_job(project_id, operation, lambda: QACoordinator(manager, FinalAssembler()).run(project_id))
        raise HTTPException(501, f"Operation {operation} is not wired to a real coordinator yet")
    return app
