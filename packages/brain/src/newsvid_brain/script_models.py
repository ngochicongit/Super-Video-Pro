from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from .models import StrictModel


class NewsStyle(StrEnum):
    BREAKING_NEWS = "breaking-news"
    TECH_NEWS = "tech-news"
    FINANCE_NEWS = "finance-news"
    EXPLAINER = "explainer"
    DOCUMENTARY = "documentary"


class SegmentType(StrEnum):
    HOOK = "hook"
    BODY = "body"
    OUTRO = "outro"


class CandidateSegment(StrictModel):
    type: SegmentType
    narration: str = Field(min_length=1)
    fact_refs: list[str] = Field(default_factory=list)


class CandidateScript(StrictModel):
    title: str = Field(min_length=1, max_length=160)
    segments: list[CandidateSegment] = Field(min_length=3, max_length=12)


class ScriptSegment(CandidateSegment):
    id: str = Field(pattern=r"^segment_[0-9]{3,}$")
    estimated_duration_seconds: float = Field(gt=0)


class NewsScript(StrictModel):
    schema_version: int = 1
    language: str = Field(default="vi", pattern=r"^vi$")
    style: NewsStyle
    target_duration_seconds: int = Field(default=60, ge=30, le=90)
    estimated_duration_seconds: float = Field(gt=0)
    title: str = Field(min_length=1, max_length=160)
    segments: list[ScriptSegment] = Field(min_length=3, max_length=12)

    @model_validator(mode="after")
    def validate_structure(self) -> "NewsScript":
        ids = [segment.id for segment in self.segments]
        if len(ids) != len(set(ids)):
            raise ValueError("Script segment IDs must be unique")
        if self.segments[0].type is not SegmentType.HOOK:
            raise ValueError("The first segment must be a hook")
        if self.segments[-1].type is not SegmentType.OUTRO:
            raise ValueError("The last segment must be an outro")
        if any(segment.type is SegmentType.HOOK for segment in self.segments[1:]):
            raise ValueError("Only the first segment may be a hook")
        if any(segment.type is SegmentType.OUTRO for segment in self.segments[:-1]):
            raise ValueError("Only the last segment may be an outro")
        return self
