from __future__ import annotations
from pathlib import Path
from .project import ProjectManager
from .config import load_config
from .doctor import collect_status
from .qa import QACoordinator
from .final_assembler import FinalAssembler

def create_app(projects_dir: Path | None = None):
    from fastapi import FastAPI, HTTPException
    config = load_config(); manager = ProjectManager(projects_dir or config.projects_dir)
    app = FastAPI(title="NewsVid API", version="0.15.0")
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
    @app.get("/services/status")
    def services(): return [s.__dict__ for s in collect_status(config)]
    @app.post("/projects/{project_id}/{operation}")
    def operation(project_id: str, operation: str):
        if operation not in {"generate", "scene", "preview", "render", "validate"}: raise HTTPException(404, "Unknown operation")
        manager.load(project_id)
        return {"project_id": project_id, "operation": operation, "status": "accepted"}
    return app
