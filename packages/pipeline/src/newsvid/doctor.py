from __future__ import annotations

import importlib.util
import shutil
import socket
import subprocess
import sys
from dataclasses import dataclass
from urllib.parse import urlparse

from .config import AppConfig


@dataclass(frozen=True)
class DependencyStatus:
    name: str
    status: str
    detail: str
    required: bool = False


def _command(name: str, args: list[str], required: bool = False) -> DependencyStatus:
    executable = shutil.which(name)
    if not executable:
        return DependencyStatus(name, "MISSING" if required else "OPTIONAL/OFFLINE", "not found on PATH", required)
    try:
        result = subprocess.run([executable, *args], capture_output=True, text=True, timeout=5, shell=False)
        line = (result.stdout or result.stderr).splitlines()[0] if (result.stdout or result.stderr) else executable
        return DependencyStatus(name, "OK" if result.returncode == 0 else "ERROR", line.strip(), required)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return DependencyStatus(name, "ERROR", str(exc), required)


def _port(name: str, url: str) -> DependencyStatus:
    parsed = urlparse(url)
    try:
        with socket.create_connection((parsed.hostname or "127.0.0.1", parsed.port or 80), timeout=0.35):
            return DependencyStatus(name, "OK", url)
    except OSError:
        return DependencyStatus(name, "OPTIONAL/OFFLINE", url)


def collect_status(config: AppConfig) -> list[DependencyStatus]:
    checks = [
        DependencyStatus("Python", "OK" if sys.version_info >= (3, 11) else "ERROR", sys.version.split()[0], True),
        _command("node", ["--version"], True),
        _command("ffmpeg", ["-version"], True),
        _command("ollama", ["--version"]),
        DependencyStatus("Qwen", "CONFIGURED", config.services.ollama_model),
        DependencyStatus("Playwright", "OK" if importlib.util.find_spec("playwright") else "OPTIONAL/OFFLINE", "Python package"),
        _port("ComfyUI", config.services.comfyui_url),
        _command("piper", ["--version"]),
        DependencyStatus("F5-TTS", "OK" if importlib.util.find_spec("f5_tts") else "OPTIONAL/OFFLINE", "Python package"),
        DependencyStatus("WhisperX", "OK" if importlib.util.find_spec("whisperx") else "OPTIONAL/OFFLINE", "Python package"),
    ]
    return checks
