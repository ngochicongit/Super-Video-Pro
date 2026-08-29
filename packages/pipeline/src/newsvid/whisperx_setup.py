from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx

from .process_env import subprocess_environment


WHISPERX_VERSION = "3.8.6"
_process: subprocess.Popen | None = None


def _python_path(root: Path) -> Path:
    return root / ".services" / "whisperx" / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _run(args: list[str], root: Path, timeout: float = 1800) -> None:
    result = subprocess.run(
        args, cwd=root, env=subprocess_environment(args[0]), shell=False,
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
    )
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout)[-2000:])


def ensure_whisperx_service(root: Path, url: str, model: str = "small") -> list[str]:
    global _process
    parsed = urlparse(url)
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise RuntimeError("Automatic WhisperX setup is restricted to a loopback endpoint")
    port = parsed.port or 8000
    try:
        if httpx.get(url.rstrip("/") + "/health", timeout=1).is_success:
            return ["WhisperX service was already running"]
    except httpx.HTTPError:
        pass

    python = _python_path(root)
    actions: list[str] = []
    if not python.is_file():
        python.parent.parent.mkdir(parents=True, exist_ok=True)
        _run([sys.executable, "-m", "venv", str(python.parent.parent)], root)
        actions.append("created isolated WhisperX environment")
    check = subprocess.run([str(python), "-c", "import whisperx,fastapi,uvicorn,multipart"], shell=False)
    if check.returncode:
        _run([str(python), "-m", "pip", "install", "--upgrade", "pip"], root)
        _run([str(python), "-m", "pip", "install", f"whisperx=={WHISPERX_VERSION}",
              "fastapi>=0.115,<1", "uvicorn>=0.34,<1", "python-multipart>=0.0.20,<1"], root)
        actions.append(f"installed WhisperX {WHISPERX_VERSION}")

    env = subprocess_environment(str(python))
    env.update({
        "PYTHONPATH": os.pathsep.join([str(root / "packages" / "pipeline" / "src"), env.get("PYTHONPATH", "")]),
        "NEWSVID_WHISPERX_MODEL": model,
        "NEWSVID_WHISPERX_DEVICE": "cpu",
        "NEWSVID_WHISPERX_COMPUTE_TYPE": "int8",
    })
    log_dir = root / ".services" / "whisperx"
    log_dir.mkdir(parents=True, exist_ok=True)
    log = (log_dir / "service.log").open("a", encoding="utf-8")
    _process = subprocess.Popen(
        [str(python), "-m", "uvicorn", "newsvid.whisperx_service:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=root, env=env, shell=False, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    for _ in range(60):
        if _process.poll() is not None:
            raise RuntimeError(f"WhisperX service exited early; see {log_dir / 'service.log'}")
        try:
            response = httpx.get(url.rstrip("/") + "/health", timeout=1)
            if response.is_success:
                actions.append(f"started WhisperX {model} on CPU int8")
                return actions
        except httpx.HTTPError:
            pass
        time.sleep(.5)
    raise RuntimeError(f"WhisperX service did not become ready; see {log_dir / 'service.log'}")
