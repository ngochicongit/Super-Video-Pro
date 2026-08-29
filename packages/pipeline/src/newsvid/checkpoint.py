from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
from typing import Any

from .persistence import atomic_write_model, load_model
from .schemas import Checkpoint, PipelineStage, StageCheckpoint, StageStatus


class CheckpointStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def initialize(self, project_id: str) -> Checkpoint:
        checkpoint = Checkpoint(project_id=project_id)
        atomic_write_model(self.path, checkpoint)
        return checkpoint

    def reconcile_artifacts(self, project_dir: Path) -> Checkpoint:
        """Invalidate completed stages whose persisted artifact disappeared or became empty."""
        expected = {
            PipelineStage.INGEST: ("article.md", "source.json", "images.json"),
            PipelineStage.FACTS: ("facts.json",), PipelineStage.SCRIPT: ("script.json",),
            PipelineStage.STORYBOARD: ("storyboard.json",),
            PipelineStage.TTS: ("audio/tts_manifest.json",),
            PipelineStage.ALIGNMENT: ("words.json", "captions/subtitles.ass", "captions/subtitle_report.json"),
            PipelineStage.VISUALS: ("images/generated_manifest.json",),
            PipelineStage.SCENES: ("scenes/manifest.json",),
            PipelineStage.PREVIEW: ("output/preview.mp4",),
            PipelineStage.QA: ("qa.json",), PipelineStage.FINAL_RENDER: ("output/final.mp4", "output/render_manifest.json"),
        }
        checkpoint = self.load()
        for stage, paths in expected.items():
            if checkpoint.stages[stage].status is not StageStatus.COMPLETED: continue
            invalid = [path for path in paths if not (project_dir / path).is_file()
                       or (project_dir / path).stat().st_size == 0]
            for relative in paths:
                artifact = project_dir / relative
                if artifact.suffix != ".json" or not artifact.is_file() or artifact.stat().st_size == 0: continue
                try:
                    payload = json.loads(artifact.read_text(encoding="utf-8"))
                    def references(value: Any):
                        if isinstance(value, dict):
                            for key, item in value.items():
                                if key in {"audio_path", "video_path", "output_path", "file_path"} and isinstance(item, str): yield item
                                else: yield from references(item)
                        elif isinstance(value, list):
                            for item in value: yield from references(item)
                    for reference in references(payload):
                        target = project_dir / reference
                        if not target.is_file() or target.stat().st_size == 0: invalid.append(reference)
                except (OSError, ValueError, TypeError): invalid.append(relative + " (invalid JSON)")
            if invalid:
                self.update(stage, StageStatus.FAILED,
                            error="ARTIFACT_INVALID: missing or empty: " + ", ".join(invalid))
                checkpoint = self.load()
        return checkpoint

    def load(self) -> Checkpoint:
        return load_model(self.path, Checkpoint)

    def update(
        self,
        stage: PipelineStage,
        status: StageStatus,
        *,
        fingerprint: str | None = None,
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Checkpoint:
        checkpoint = self.load()
        now = datetime.now(timezone.utc)
        previous = checkpoint.stages[stage]
        checkpoint.stages[stage] = StageCheckpoint(
            status=status,
            fingerprint=fingerprint if fingerprint is not None else previous.fingerprint,
            started_at=now if status is StageStatus.RUNNING and previous.started_at is None else previous.started_at,
            completed_at=now if status is StageStatus.COMPLETED else None,
            error=error,
            metadata=metadata if metadata is not None else previous.metadata,
        )
        checkpoint.updated_at = now
        atomic_write_model(self.path, checkpoint)
        return checkpoint
