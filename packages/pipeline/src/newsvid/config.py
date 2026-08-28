from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field


class ServiceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:7b"
    ollama_temperature: float = Field(default=0.1, ge=0, le=2)
    ollama_timeout_seconds: float = Field(default=120, gt=0)
    ollama_max_attempts: int = Field(default=3, ge=1, le=5)
    comfyui_url: str = "http://127.0.0.1:8188"


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    projects_dir: Path = Path("projects")
    log_level: str = Field(default="INFO", pattern=r"^(DEBUG|INFO|WARNING|ERROR)$")
    services: ServiceConfig = Field(default_factory=ServiceConfig)


def load_config(path: Path | None = None) -> AppConfig:
    config_path = path or Path(os.environ.get("NEWSVID_CONFIG", "config/app.yaml"))
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
    config = AppConfig.model_validate(raw or {})
    project_override = os.environ.get("NEWSVID_PROJECTS_DIR")
    if project_override:
        config.projects_dir = Path(project_override)
    elif not config.projects_dir.is_absolute():
        config.projects_dir = (config_path.parent.parent / config.projects_dir).resolve()
    return config
