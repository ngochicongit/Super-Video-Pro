from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
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
