from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PipelineStage(StrEnum):
    INGEST = "INGEST"
    FACTS = "FACTS"
    SCRIPT = "SCRIPT"
    STORYBOARD = "STORYBOARD"
    TTS = "TTS"
    ALIGNMENT = "ALIGNMENT"
    VISUALS = "VISUALS"
    SCENES = "SCENES"
    PREVIEW = "PREVIEW"
    QA = "QA"
    FINAL_RENDER = "FINAL_RENDER"


class StageStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class StageCheckpoint(StrictModel):
    status: StageStatus = StageStatus.PENDING
    fingerprint: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Checkpoint(StrictModel):
    schema_version: int = 1
    project_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,63}$")
    updated_at: datetime = Field(default_factory=utc_now)
    stages: dict[PipelineStage, StageCheckpoint] = Field(
        default_factory=lambda: {stage: StageCheckpoint() for stage in PipelineStage}
    )


class Project(StrictModel):
    schema_version: int = 1
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,63}$")
    name: str = Field(min_length=1, max_length=120)
    status: str = "draft"
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
