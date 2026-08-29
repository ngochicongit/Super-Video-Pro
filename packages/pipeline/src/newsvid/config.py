from __future__ import annotations

import os
from importlib.resources import files
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
    comfyui_checkpoint: str = "sd_xl_base_1.0.safetensors"
    comfyui_timeout_seconds: float = Field(default=300, gt=0)
    comfyui_poll_interval_seconds: float = Field(default=2, gt=0, le=30)
    comfyui_workflow_dir: Path = Path("workflows/comfyui")
    tts_provider: str = Field(default="piper", pattern=r"^(piper|f5tts)$")
    tts_voice: str = "vi_VN-vais1000-medium"
    tts_speed: float = Field(default=1.0, ge=0.5, le=2.0)
    tts_timeout_seconds: float = Field(default=120, gt=0)
    piper_executable: str = "piper"
    piper_model_path: Path = Path("models/piper/vi_VN-vais1000-medium.onnx")
    f5tts_url: str = "http://127.0.0.1:7860"
    whisperx_url: str = "http://127.0.0.1:8000"
    whisperx_model: str = "large-v3"
    whisperx_timeout_seconds: float = Field(default=300, gt=0)
    subtitle_top_safe_px: int = Field(default=180, ge=0)
    subtitle_bottom_safe_px: int = Field(default=300, ge=0)
    subtitle_max_words_per_line: int = Field(default=7, ge=1, le=12)
    ffmpeg_executable: str = "ffmpeg"
    ffprobe_executable: str = "ffprobe"
    image_max_bytes: int = Field(default=20 * 1024 * 1024, ge=1024)
    node_executable: str = "node"
    chromium_executable: Path = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    projects_dir: Path = Path("projects")
    pronunciation_path: Path = Path("config/pronunciation_vi.yaml")
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
    if not config.pronunciation_path.is_absolute():
        config.pronunciation_path = (config_path.parent.parent / config.pronunciation_path).resolve()
    if not config.pronunciation_path.is_file():
        packaged = files("newsvid_brain").joinpath("data/pronunciation_vi.yaml")
        if packaged.is_file():
            config.pronunciation_path = Path(str(packaged))
    if not config.services.piper_model_path.is_absolute():
        config.services.piper_model_path = (config_path.parent.parent / config.services.piper_model_path).resolve()
    if not config.services.comfyui_workflow_dir.is_absolute():
        config.services.comfyui_workflow_dir = (config_path.parent.parent / config.services.comfyui_workflow_dir).resolve()
    if not config.services.comfyui_workflow_dir.is_dir():
        packaged_workflows = files("newsvid").joinpath("data/comfyui")
        if packaged_workflows.is_dir():
            config.services.comfyui_workflow_dir = Path(str(packaged_workflows))
    if os.environ.get("COMFYUI_URL"):
        config.services.comfyui_url = os.environ["COMFYUI_URL"]
    if os.environ.get("OLLAMA_URL"):
        config.services.ollama_url = os.environ["OLLAMA_URL"]
    if os.environ.get("OLLAMA_MODEL"):
        config.services.ollama_model = os.environ["OLLAMA_MODEL"]
    if os.environ.get("COMFYUI_CHECKPOINT"):
        config.services.comfyui_checkpoint = os.environ["COMFYUI_CHECKPOINT"]
    if os.environ.get("NEWSVID_FFMPEG"):
        config.services.ffmpeg_executable = os.environ["NEWSVID_FFMPEG"]
    if os.environ.get("NEWSVID_FFPROBE"):
        config.services.ffprobe_executable = os.environ["NEWSVID_FFPROBE"]
    if os.environ.get("NEWSVID_NODE"):
        config.services.node_executable = os.environ["NEWSVID_NODE"]
    if os.environ.get("NEWSVID_CHROMIUM"):
        config.services.chromium_executable = Path(os.environ["NEWSVID_CHROMIUM"])
    return config
