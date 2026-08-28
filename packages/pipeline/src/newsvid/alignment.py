from __future__ import annotations

import hashlib

from newsvid_brain import (AlignmentError, AlignmentProvider, SceneAlignment,
                           Storyboard, SubtitleLayout, SubtitleReport,
                           WordsDocument, generate_ass)
from newsvid_brain.tts_models import TTSManifest

from .checkpoint import CheckpointStore
from .persistence import atomic_write_model, atomic_write_text, load_model
from .project import ProjectManager
from .schemas import PipelineStage, StageStatus


class AlignmentCoordinator:
    def __init__(self, projects: ProjectManager, provider: AlignmentProvider,
                 layout: SubtitleLayout | None = None) -> None:
        self.projects = projects
        self.provider = provider
        self.layout = layout or SubtitleLayout()

    def generate(self, project_id: str) -> tuple[WordsDocument, SubtitleReport]:
        directory = self.projects.project_dir(project_id)
        self.projects.load(project_id)
        storyboard = load_model(directory / "storyboard.json", Storyboard)
        manifest = load_model(directory / "audio" / "tts_manifest.json", TTSManifest)
        entries = {entry.scene_id: entry for entry in manifest.entries}
        if set(entries) != {scene.id for scene in storyboard.scenes}:
            raise AlignmentError("TTS manifest does not cover every storyboard scene")
        digest = hashlib.sha256()
        for value in (storyboard.model_dump_json(), manifest.model_dump_json(),
                      self.provider.name, self.provider.cache_key,
                      self.layout.model_dump_json()):
            digest.update(value.encode("utf-8"))
        fingerprint = f"sha256:{digest.hexdigest()}"
        words_path = directory / "words.json"
        ass_path = directory / "captions" / "subtitles.ass"
        report_path = directory / "captions" / "subtitle_report.json"
        store = CheckpointStore(directory / "checkpoint.json")
        previous = store.load().stages[PipelineStage.ALIGNMENT]
        if previous.status is StageStatus.COMPLETED and previous.fingerprint == fingerprint:
            try:
                cached = load_model(words_path, WordsDocument)
                report = load_model(report_path, SubtitleReport)
                if cached.fingerprint == fingerprint and ass_path.is_file():
                    return cached, report
            except (OSError, ValueError):
                pass
        store.update(PipelineStage.ALIGNMENT, StageStatus.RUNNING, fingerprint=fingerprint)
        try:
            scenes: list[SceneAlignment] = []
            offset = 0.0
            for scene in storyboard.scenes:
                entry = entries[scene.id]
                words = self.provider.align(directory / entry.relative_path,
                                            entry.normalized_text, language="vi")
                scenes.append(SceneAlignment(
                    scene_id=scene.id, audio_path=entry.relative_path,
                    text=entry.normalized_text, offset_seconds=round(offset, 6),
                    duration_seconds=entry.duration_seconds, words=words,
                ))
                offset += entry.duration_seconds
            document = WordsDocument(provider=self.provider.name,
                                     fingerprint=fingerprint, scenes=scenes)
            ass, report = generate_ass(document, self.layout)
            atomic_write_model(words_path, document)
            atomic_write_text(ass_path, ass)
            atomic_write_model(report_path, report)
            store.update(PipelineStage.ALIGNMENT, StageStatus.COMPLETED,
                         fingerprint=fingerprint,
                         metadata={"provider": self.provider.name,
                                   "word_count": sum(len(scene.words) for scene in scenes),
                                   "dialogue_count": report.dialogue_count,
                                   "ass_path": report.ass_path,
                                   "overflow_detected": report.overflow_detected})
            return document, report
        except Exception as exc:
            store.update(PipelineStage.ALIGNMENT, StageStatus.FAILED,
                         fingerprint=fingerprint, error=f"{type(exc).__name__}: {exc}")
            raise
