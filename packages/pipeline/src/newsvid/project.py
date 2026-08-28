from __future__ import annotations

import re
import secrets
import unicodedata
from pathlib import Path

from .checkpoint import CheckpointStore
from .persistence import atomic_write_model, load_model
from .schemas import Project

PROJECT_DIRS = ("audio", "images", "clips", "captions", "scenes", "cache", "logs", "output")


def _slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")[:40] or "project"


class ProjectManager:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def project_dir(self, project_id: str) -> Path:
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", project_id):
            raise ValueError("Invalid project id")
        candidate = (self.root / project_id).resolve()
        if candidate.parent != self.root:
            raise ValueError("Project path escapes the configured root")
        return candidate

    def create(self, name: str) -> Project:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Project name is required")
        for _ in range(10):
            project_id = f"{_slug(clean_name)}-{secrets.token_hex(3)}"
            directory = self.project_dir(project_id)
            try:
                directory.mkdir(parents=True, exist_ok=False)
                break
            except FileExistsError:
                continue
        else:
            raise RuntimeError("Could not allocate a unique project id")
        for child in PROJECT_DIRS:
            (directory / child).mkdir()
        project = Project(id=project_id, name=clean_name)
        atomic_write_model(directory / "project.json", project)
        CheckpointStore(directory / "checkpoint.json").initialize(project_id)
        return project

    def load(self, project_id: str) -> Project:
        return load_model(self.project_dir(project_id) / "project.json", Project)

    def list(self) -> list[Project]:
        projects: list[Project] = []
        if not self.root.exists():
            return projects
        for path in self.root.iterdir():
            try:
                projects.append(load_model(path / "project.json", Project))
            except (OSError, ValueError):
                continue
        return sorted(projects, key=lambda item: item.updated_at, reverse=True)
