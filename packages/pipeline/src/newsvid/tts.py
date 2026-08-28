from __future__ import annotations

import hashlib
import wave
from pathlib import Path

from newsvid_brain import Storyboard, TTSError
from newsvid_brain.normalize_vi import (PronunciationConfig, normalize_vi,
                                        pronunciation_fingerprint)
from newsvid_brain.tts_models import AudioCacheEntry, TTSManifest
from newsvid_brain.tts_providers import TTSProvider, validate_wav

from .checkpoint import CheckpointStore
from .persistence import atomic_write_model, load_model
from .project import ProjectManager
from .schemas import PipelineStage, StageStatus


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _duration(path: Path) -> float:
    with wave.open(str(path), "rb") as stream:
        return stream.getnframes() / stream.getframerate()


class TTSCoordinator:
    def __init__(self, projects: ProjectManager, provider: TTSProvider,
                 pronunciation: PronunciationConfig, *, voice: str) -> None:
        self.projects = projects
        self.provider = provider
        self.pronunciation = pronunciation
        self.voice = voice

    def generate(self, project_id: str) -> TTSManifest:
        directory = self.projects.project_dir(project_id)
        self.projects.load(project_id)
        storyboard = load_model(directory / "storyboard.json", Storyboard)
        pronunciation_key = pronunciation_fingerprint(self.pronunciation)
        digest = hashlib.sha256()
        for value in (storyboard.model_dump_json(), self.provider.name, self.provider.cache_key,
                      self.voice, pronunciation_key):
            digest.update(value.encode("utf-8"))
        stage_fingerprint = f"sha256:{digest.hexdigest()}"
        store = CheckpointStore(directory / "checkpoint.json")
        manifest_path = directory / "audio" / "tts_manifest.json"
        try:
            manifest = load_model(manifest_path, TTSManifest)
        except (OSError, ValueError):
            manifest = TTSManifest(provider=self.provider.name, voice=self.voice,
                                   provider_config_fingerprint=self.provider.cache_key,
                                   pronunciation_fingerprint=pronunciation_key)
        entries = {entry.scene_id: entry for entry in manifest.entries}
        store.update(PipelineStage.TTS, StageStatus.RUNNING, fingerprint=stage_fingerprint)
        cache_hits = 0
        generated = 0
        try:
            for scene in storyboard.scenes:
                normalized = normalize_vi(scene.narration, self.pronunciation)
                item_digest = hashlib.sha256()
                for value in (scene.narration, normalized, self.voice, self.provider.name,
                              self.provider.cache_key, pronunciation_key):
                    item_digest.update(value.encode("utf-8"))
                fingerprint = f"sha256:{item_digest.hexdigest()}"
                output = directory / "audio" / f"{scene.id}.wav"
                previous = entries.get(scene.id)
                if previous and previous.fingerprint == fingerprint and output.is_file():
                    try:
                        validate_wav(output)
                        if _sha256_file(output) == previous.audio_sha256:
                            cache_hits += 1
                            continue
                    except TTSError:
                        pass
                self.provider.synthesize(normalized, output, voice=self.voice)
                validate_wav(output)
                entries[scene.id] = AudioCacheEntry(
                    scene_id=scene.id, relative_path=f"audio/{scene.id}.wav",
                    fingerprint=fingerprint, audio_sha256=_sha256_file(output),
                    normalized_text=normalized, duration_seconds=round(_duration(output), 6),
                )
                generated += 1
                manifest = self._manifest(entries, storyboard, pronunciation_key)
                atomic_write_model(manifest_path, manifest)
            manifest = self._manifest(entries, storyboard, pronunciation_key)
            atomic_write_model(manifest_path, manifest)
            store.update(PipelineStage.TTS, StageStatus.COMPLETED, fingerprint=stage_fingerprint,
                         metadata={"provider": self.provider.name, "voice": self.voice,
                                   "scene_count": len(manifest.entries), "cache_hits": cache_hits,
                                   "generated": generated})
            return manifest
        except Exception as exc:
            store.update(PipelineStage.TTS, StageStatus.FAILED, fingerprint=stage_fingerprint,
                         error=f"{type(exc).__name__}: {exc}")
            raise

    def _manifest(self, entries: dict[str, AudioCacheEntry], storyboard: Storyboard,
                  pronunciation_key: str) -> TTSManifest:
        ordered = [entries[scene.id] for scene in storyboard.scenes if scene.id in entries]
        return TTSManifest(provider=self.provider.name, voice=self.voice,
                           provider_config_fingerprint=self.provider.cache_key,
                           pronunciation_fingerprint=pronunciation_key, entries=ordered)
