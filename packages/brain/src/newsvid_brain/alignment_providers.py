from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Callable, Protocol
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, ConfigDict, Field

from .alignment_models import WordTiming
from .errors import AlignmentError


class AlignmentProvider(Protocol):
    name: str

    @property
    def cache_key(self) -> str: ...

    def align(self, audio_path: Path, text: str, *, language: str = "vi") -> list[WordTiming]: ...


class WhisperXConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    base_url: str = "http://127.0.0.1:8000"
    model: str = "large-v3"
    timeout_seconds: float = Field(default=300, gt=0)
    max_attempts: int = Field(default=3, ge=1, le=5)


class WhisperXProvider:
    """Adapter for an isolated local WhisperX OpenAI-compatible endpoint."""

    name = "whisperx"

    def __init__(self, config: WhisperXConfig, *, transport: httpx.BaseTransport | None = None,
                 sleeper: Callable[[float], None] = time.sleep) -> None:
        host = (urlparse(config.base_url).hostname or "").casefold()
        if host not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("WhisperX endpoint must use a loopback host")
        self.config = config
        self.transport = transport
        self.sleeper = sleeper

    @property
    def cache_key(self) -> str:
        raw = json.dumps(self.config.model_dump(mode="json"), sort_keys=True).encode()
        return f"sha256:{hashlib.sha256(raw).hexdigest()}"

    def align(self, audio_path: Path, text: str, *, language: str = "vi") -> list[WordTiming]:
        if not audio_path.is_file():
            raise AlignmentError(f"Audio file not found: {audio_path}")
        endpoint = f"{self.config.base_url.rstrip('/')}/v1/audio/alignments"
        last_error = "unknown error"
        for attempt in range(1, self.config.max_attempts + 1):
            try:
                with httpx.Client(timeout=self.config.timeout_seconds,
                                  transport=self.transport) as client:
                    with audio_path.open("rb") as stream:
                        response = client.post(
                            endpoint,
                            data={"model": self.config.model, "language": language,
                                  "text": text, "response_format": "verbose_json",
                                  "timestamp_granularities": "word"},
                            files={"file": (audio_path.name, stream, "audio/wav")},
                        )
                response.raise_for_status()
                payload = response.json()
                raw_words = payload.get("words")
                if not isinstance(raw_words, list):
                    raise AlignmentError("WhisperX response has no word timestamp list")
                words = [WordTiming.model_validate(item) for item in raw_words]
                if not words:
                    raise AlignmentError("WhisperX returned no aligned words")
                return words
            except (httpx.HTTPError, ValueError, AlignmentError) as exc:
                last_error = str(exc)
                if attempt < self.config.max_attempts:
                    self.sleeper(min(2 ** (attempt - 1), 4))
        raise AlignmentError(f"WhisperX alignment failed after {self.config.max_attempts} attempts: {last_error}")
