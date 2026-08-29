from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Callable

import httpx


Progress = Callable[[float, str, str], None]


def find_ollama() -> str | None:
    found = shutil.which("ollama")
    if found:
        return found
    local = os.environ.get("LOCALAPPDATA")
    if local:
        candidate = Path(local) / "Programs" / "Ollama" / "ollama.exe"
        if candidate.is_file():
            return str(candidate)
    return None


class OllamaSetupCoordinator:
    """Install/start Ollama and pull one configured model with real CLI progress."""

    def __init__(self, base_url: str, *, runner=subprocess.Popen,
                 http_get=httpx.get, sleeper=time.sleep) -> None:
        self.base_url = base_url.rstrip("/")
        self._runner = runner
        self._http_get = http_get
        self._sleep = sleeper

    def setup(self, model: str, progress: Progress) -> dict[str, str]:
        progress(.02, "ollama:checking", "Đang kiểm tra Ollama")
        executable = find_ollama()
        if not executable:
            progress(.08, "ollama:installing", "Đang cài Ollama bằng Windows Package Manager")
            winget = shutil.which("winget")
            if not winget:
                raise RuntimeError("Không tìm thấy winget. Hãy cài App Installer từ Microsoft Store.")
            self._run(
                [winget, "install", "--id", "Ollama.Ollama", "-e", "--silent",
                 "--accept-package-agreements", "--accept-source-agreements"],
                lambda percent, line: progress(.08 + percent * .27, "ollama:installing", line),
            )
            executable = find_ollama()
            if not executable:
                raise RuntimeError("Ollama đã cài nhưng không tìm thấy ollama.exe. Hãy khởi động lại ứng dụng.")

        if not self._online():
            progress(.38, "ollama:starting", "Đang khởi động dịch vụ Ollama")
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            self._runner([executable, "serve"], stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, shell=False, creationflags=creationflags)
            for _ in range(40):
                if self._online():
                    break
                self._sleep(.25)
            else:
                raise RuntimeError(f"Ollama không sẵn sàng tại {self.base_url} sau khi khởi động.")

        progress(.42, "ollama:downloading", f"Đang tải model {model}")
        self._run(
            [executable, "pull", model],
            lambda percent, line: progress(.42 + percent * .53, "ollama:downloading", line),
        )
        progress(.97, "ollama:verifying", f"Đang xác minh model {model}")
        models = self._models()
        if model not in models:
            raise RuntimeError(f"Tải hoàn tất nhưng Ollama không báo model '{model}' đã sẵn sàng.")
        return {"status": "ready", "model": model, "base_url": self.base_url}

    def _online(self) -> bool:
        try:
            response = self._http_get(f"{self.base_url}/api/tags", timeout=1)
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    def _models(self) -> set[str]:
        response = self._http_get(f"{self.base_url}/api/tags", timeout=3)
        response.raise_for_status()
        return {str(item.get("name", "")) for item in response.json().get("models", [])}

    def _run(self, command: list[str], update: Callable[[float, str], None]) -> None:
        process = self._runner(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding="utf-8", errors="replace", shell=False)
        latest = "Đang xử lý..."
        assert process.stdout is not None
        for chunk in iter(lambda: process.stdout.read(1), ""):
            latest += chunk
            if chunk in {"\r", "\n"}:
                clean = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", latest).strip()
                match = re.search(r"(\d{1,3})\s*%", clean)
                update(min(1.0, int(match.group(1)) / 100) if match else 0.0,
                       clean[-180:] or "Đang xử lý...")
                latest = ""
        code = process.wait()
        if code:
            raise RuntimeError(f"Lệnh thất bại ({code}): {' '.join(command[:3])}; {latest.strip()}")


def save_service_settings(path: Path, **settings: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    existing = {}
    if path.is_file():
        try: existing = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError): pass
    existing.update(settings)
    temporary.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)
