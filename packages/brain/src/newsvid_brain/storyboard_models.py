from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import Field, HttpUrl, model_validator

from .models import StrictModel
from .script_models import NewsStyle


class SceneType(StrEnum):
    HOOK = "hook"
    HEADLINE = "headline"
    ARTICLE_IMAGE = "article-image"
    KINETIC_TEXT = "kinetic-text"
    STAT_HERO = "stat-hero"
    CHART = "chart"
    COMPARISON = "comparison"
    FEATURE_LIST = "feature-list"
    TIMELINE = "timeline"
    QUOTE = "quote"
    SCREENSHOT = "screenshot"
    AI_ILLUSTRATION = "AI-illustration"
    MAP = "map"
    OUTRO = "outro"


class SourceType(StrEnum):
    ARTICLE = "article"
    GENERATED = "generated"
    STOCK = "stock"
    USER = "user"
    GRAPHIC = "graphic"
    SCREENSHOT = "screenshot"


class VisualProvenance(StrictModel):
    source_type: SourceType
    source_url: HttpUrl | None = None
    local_path: str | None = None
    generator: str | None = None
    workflow: str | None = None

    @model_validator(mode="after")
    def required_details(self) -> "VisualProvenance":
        if self.source_type in {SourceType.ARTICLE, SourceType.STOCK, SourceType.SCREENSHOT}:
            if self.source_url is None and not self.local_path:
                raise ValueError(f"{self.source_type.value} provenance requires source_url or local_path")
        if self.source_type is SourceType.GENERATED and (not self.generator or not self.workflow):
            raise ValueError("Generated provenance requires generator and workflow")
        return self


class VisualPlan(StrictModel):
    type: SceneType
    template: str = Field(min_length=1)
    provenance: VisualProvenance
    prompt: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def compatible_provenance(self) -> "VisualPlan":
        if self.type is SceneType.ARTICLE_IMAGE and self.provenance.source_type is not SourceType.ARTICLE:
            raise ValueError("article-image requires article provenance")
        if self.type is SceneType.SCREENSHOT and self.provenance.source_type is not SourceType.SCREENSHOT:
            raise ValueError("screenshot requires screenshot provenance")
        if self.type is SceneType.AI_ILLUSTRATION:
            if self.provenance.source_type is not SourceType.GENERATED or not self.prompt:
                raise ValueError("AI-illustration requires generated provenance and a prompt")
        graphic_types = {SceneType.HOOK, SceneType.HEADLINE, SceneType.KINETIC_TEXT,
                         SceneType.STAT_HERO, SceneType.CHART, SceneType.COMPARISON,
                         SceneType.FEATURE_LIST, SceneType.TIMELINE, SceneType.QUOTE,
                         SceneType.MAP, SceneType.OUTRO}
        if self.type in graphic_types and self.provenance.source_type is not SourceType.GRAPHIC:
            raise ValueError(f"{self.type.value} requires graphic provenance")
        return self


class StoryboardVideo(StrictModel):
    width: int = Field(default=1080, ge=320)
    height: int = Field(default=1920, ge=320)
    fps: int = Field(default=30, ge=1, le=120)
    target_duration: int = Field(ge=30, le=90)
    style: NewsStyle


class StoryboardScene(StrictModel):
    id: str = Field(pattern=r"^scene_[0-9]{3,}$")
    script_segment_id: str = Field(pattern=r"^segment_[0-9]{3,}$")
    type: SceneType
    narration: str = Field(min_length=1)
    fact_refs: list[str] = Field(min_length=1)
    duration_seconds: float = Field(gt=0)
    visual: VisualPlan


class Storyboard(StrictModel):
    schema_version: int = 1
    video: StoryboardVideo
    scenes: list[StoryboardScene] = Field(min_length=1, max_length=30)

    @model_validator(mode="after")
    def stable_sequence(self) -> "Storyboard":
        ids = [scene.id for scene in self.scenes]
        segment_ids = [scene.script_segment_id for scene in self.scenes]
        if len(ids) != len(set(ids)) or len(segment_ids) != len(set(segment_ids)):
            raise ValueError("Storyboard scene and script segment IDs must be unique")
        return self
