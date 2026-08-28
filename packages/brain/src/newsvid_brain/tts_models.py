from __future__ import annotations

from pydantic import Field

from .models import StrictModel


class AudioCacheEntry(StrictModel):
    scene_id: str = Field(pattern=r"^scene_[0-9]{3,}$")
    relative_path: str = Field(pattern=r"^audio/scene_[0-9]{3,}\.wav$")
    fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    audio_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    normalized_text: str = Field(min_length=1)
    duration_seconds: float = Field(gt=0)


class TTSManifest(StrictModel):
    schema_version: int = 1
    provider: str = Field(min_length=1)
    voice: str = Field(min_length=1)
    provider_config_fingerprint: str = Field(min_length=1)
    pronunciation_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    entries: list[AudioCacheEntry] = Field(default_factory=list)
