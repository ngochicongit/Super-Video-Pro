from __future__ import annotations

import importlib.util
import shutil
import socket
import subprocess
import sys
import httpx
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


def _ollama(config: AppConfig) -> DependencyStatus:
    url = config.services.ollama_url.rstrip("/")
    model = config.services.ollama_model
    try:
        response = httpx.get(f"{url}/api/tags", timeout=1.5)
        response.raise_for_status()
        installed = {
            str(item.get("name", ""))
            for item in response.json().get("models", [])
            if isinstance(item, dict)
        }
        aliases = {name.split(":", 1)[0] for name in installed}
        available = model in installed or (":" not in model and model in aliases)
        if available:
            return DependencyStatus("Ollama", "OK", f"{model} ready at {url}", True)
        return DependencyStatus(
            "Ollama", "MODEL_MISSING",
            f"Dịch vụ đang chạy nhưng thiếu model '{model}'. Dùng nút tự động thiết lập để tải "
            f"model nhẹ {config.services.ollama_setup_model}.", True,
        )
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        return DependencyStatus(
            "Ollama", "OFFLINE",
            f"Không kết nối được {url}. Dùng nút tự động thiết lập để cài Ollama và tải "
            f"model nhẹ {config.services.ollama_setup_model}. ({exc})", True,
        )


def collect_status(config: AppConfig) -> list[DependencyStatus]:
    repository_root = Path(__file__).resolve().parents[4]
    node_playwright = repository_root / "node_modules" / "playwright" / "package.json"
    gsap = repository_root / "node_modules" / "gsap" / "dist" / "gsap.min.js"
    checks = [
        DependencyStatus("Python", "OK" if sys.version_info >= (3, 11) else "ERROR", sys.version.split()[0], True),
        _command("node", ["--version"], True),
        _command("ffmpeg", ["-version"], True),
        _command("ffprobe", ["-version"], True),
        DependencyStatus("Chromium", "OK" if config.services.chromium_executable.is_file() else "MISSING",
                         str(config.services.chromium_executable), True),
        DependencyStatus("Motion", "OK" if node_playwright.is_file() and gsap.is_file() else "MISSING",
                         "Playwright 1.58.2 + GSAP 3.14.2", True),
        _ollama(config),
        _playwright(),
        _port("ComfyUI", config.services.comfyui_url),
        _command("piper", ["--version"]),
        _port("F5-TTS", config.services.f5tts_url),
        _port("WhisperX", config.services.whisperx_url),
    ]
    return checks
