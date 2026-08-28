from __future__ import annotations

import hashlib
import os
import subprocess
import tempfile
import time
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol
from urllib.parse import urlparse

import httpx

from .errors import TTSError


class TTSProvider(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def cache_key(self) -> str: ...

    def synthesize(self, text: str, output_path: Path, *, voice: str) -> Path: ...


def validate_wav(path: Path) -> None:
    try:
        with wave.open(str(path), "rb") as stream:
            if stream.getnchannels() not in {1, 2}:
                raise TTSError("WAV must contain one or two channels")
            if stream.getsampwidth() not in {1, 2, 3, 4}:
                raise TTSError("WAV has an unsupported sample width")
            if stream.getframerate() <= 0 or stream.getnframes() <= 0:
                raise TTSError("WAV contains no audio frames")
    except (wave.Error, EOFError, OSError) as exc:
        raise TTSError(f"Invalid WAV output: {path}") from exc


def _temporary_path(output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(prefix=f".{output_path.stem}.", suffix=".wav", dir=output_path.parent)
    os.close(handle)
    return Path(name)


@dataclass(frozen=True)
class PiperConfig:
    model_path: Path
    executable: str = "piper"
    voice_name: str = "vi_VN-vais1000-medium"
    speed: float = 1.0
    speaker_id: int | None = None
    timeout_seconds: float = 120


class PiperProvider:
    def __init__(self, config: PiperConfig, *,
                 runner: Callable[..., subprocess.CompletedProcess[bytes]] = subprocess.run) -> None:
        self.config = config
        self._runner = runner

    @property
    def name(self) -> str:
        return "piper"

    @property
    def cache_key(self) -> str:
        model = self.config.model_path
        identity = str(model.resolve())
        if model.exists():
            stat = model.stat()
            identity += f":{stat.st_size}:{stat.st_mtime_ns}"
        raw = f"piper:{self.config.executable}:{identity}:{self.config.voice_name}:{self.config.speed}:{self.config.speaker_id}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def synthesize(self, text: str, output_path: Path, *, voice: str) -> Path:
        if voice != self.config.voice_name:
            raise TTSError(f"Piper voice '{voice}' does not match configured model voice '{self.config.voice_name}'")
        if not self.config.model_path.is_file():
            raise TTSError(f"Piper model not found: {self.config.model_path}")
        temporary = _temporary_path(output_path)
        args = [self.config.executable, "--model", str(self.config.model_path),
                "--output_file", str(temporary), "--length_scale", str(1 / self.config.speed)]
        if self.config.speaker_id is not None:
            args.extend(["--speaker", str(self.config.speaker_id)])
        try:
            result = self._runner(args, input=text.encode("utf-8"), stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, timeout=self.config.timeout_seconds,
                                  check=False, shell=False)
            if result.returncode != 0:
                detail = result.stderr.decode("utf-8", errors="replace")[-500:]
                raise TTSError(f"Piper exited with code {result.returncode}: {detail}")
            validate_wav(temporary)
            os.replace(temporary, output_path)
            return output_path
        except FileNotFoundError as exc:
            raise TTSError(f"Piper executable not found: {self.config.executable}") from exc
        except subprocess.TimeoutExpired as exc:
            raise TTSError(f"Piper timed out after {self.config.timeout_seconds:g} seconds") from exc
        finally:
            temporary.unlink(missing_ok=True)


@dataclass(frozen=True)
class F5TTSConfig:
    base_url: str = "http://127.0.0.1:7860"
    speed: float = 1.0
    timeout_seconds: float = 120
    max_attempts: int = 3


class F5TTSProvider:
    """Optional adapter for an isolated local F5-TTS Vietnamese HTTP service."""

    def __init__(self, config: F5TTSConfig, *, transport: httpx.BaseTransport | None = None,
                 sleeper: Callable[[float], None] = time.sleep) -> None:
        host = (urlparse(config.base_url).hostname or "").casefold()
        if host not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("F5-TTS must use an isolated loopback service URL")
        self.config = config
        self._transport = transport
        self._sleeper = sleeper

    @property
    def name(self) -> str:
        return "f5tts"

    @property
    def cache_key(self) -> str:
        raw = f"f5tts:{self.config.base_url.rstrip('/')}:{self.config.speed}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def synthesize(self, text: str, output_path: Path, *, voice: str) -> Path:
        endpoint = f"{self.config.base_url.rstrip('/')}/v1/tts"
        last_error: Exception | None = None
        for attempt in range(1, self.config.max_attempts + 1):
            try:
                with httpx.Client(timeout=self.config.timeout_seconds, transport=self._transport) as client:
                    response = client.post(endpoint, json={"text": text, "voice": voice,
                                                           "language": "vi", "speed": self.config.speed,
                                                           "format": "wav"})
                    response.raise_for_status()
                temporary = _temporary_path(output_path)
                try:
                    temporary.write_bytes(response.content)
                    validate_wav(temporary)
                    os.replace(temporary, output_path)
                finally:
                    temporary.unlink(missing_ok=True)
                return output_path
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if exc.response.status_code not in {429, 500, 502, 503, 504}:
                    break
            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout,
                    httpx.WriteTimeout, httpx.PoolTimeout) as exc:
                last_error = exc
            except TTSError:
                raise
            if attempt < self.config.max_attempts:
                self._sleeper(0.25 * (2 ** (attempt - 1)))
        raise TTSError(f"F5-TTS request failed after {attempt} attempt(s)") from last_error
