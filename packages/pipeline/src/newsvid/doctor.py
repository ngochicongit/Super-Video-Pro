from __future__ import annotations

import importlib.util
import shutil
import socket
import subprocess
import sys
from pathlib import Path
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


def _playwright() -> DependencyStatus:
    if not importlib.util.find_spec("playwright"):
        return DependencyStatus("Playwright", "OPTIONAL/OFFLINE", "install with .[browser]")
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as runtime:
            executable = Path(runtime.chromium.executable_path)
        if executable.is_file():
            return DependencyStatus("Playwright", "OK", str(executable))
        return DependencyStatus("Playwright", "OPTIONAL/OFFLINE", "Chromium browser is not installed")
    except Exception as exc:
        return DependencyStatus("Playwright", "OPTIONAL/OFFLINE", str(exc))


def collect_status(config: AppConfig) -> list[DependencyStatus]:
    checks = [
        DependencyStatus("Python", "OK" if sys.version_info >= (3, 11) else "ERROR", sys.version.split()[0], True),
        _command("node", ["--version"], True),
        _command("ffmpeg", ["-version"], True),
        _command("ollama", ["--version"]),
        DependencyStatus("Qwen", "CONFIGURED", config.services.ollama_model),
        _playwright(),
        _port("ComfyUI", config.services.comfyui_url),
        _command("piper", ["--version"]),
        _port("F5-TTS", config.services.f5tts_url),
        _port("WhisperX", config.services.whisperx_url),
    ]
    return checks
