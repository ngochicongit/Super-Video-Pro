from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import Field, model_validator

from .models import StrictModel


class MotionTemplate(StrEnum):
    HOOK = "hook"
    HEADLINE = "headline"
    STAT_HERO = "stat-hero"
    CHART = "chart"
    COMPARISON = "comparison"
    TIMELINE = "timeline"
    QUOTE = "quote"
    OUTRO = "outro"


class MotionTemplateInput(StrictModel):
    template: MotionTemplate
    duration_seconds: float = Field(ge=0.25, le=30)
    width: int = Field(default=1080, ge=320)
    height: int = Field(default=1920, ge=320)
    fps: int = Field(default=30, ge=1, le=60)
    data: dict[str, Any]

    @model_validator(mode="after")
    def validate_template_data(self) -> "MotionTemplateInput":
        required = {
            MotionTemplate.HOOK: ("headline",), MotionTemplate.HEADLINE: ("headline",),
            MotionTemplate.STAT_HERO: ("value", "label"), MotionTemplate.CHART: ("title", "data"),
            MotionTemplate.COMPARISON: ("left", "right"), MotionTemplate.TIMELINE: ("items",),
            MotionTemplate.QUOTE: ("quote",), MotionTemplate.OUTRO: ("headline",),
        }[self.template]
        missing = [key for key in required if not self.data.get(key)]
        if missing:
            raise ValueError(f"{self.template.value} requires: {', '.join(missing)}")
        if self.template is MotionTemplate.CHART:
            data = self.data["data"]
            if not isinstance(data, list) or not 2 <= len(data) <= 8:
                raise ValueError("chart data must contain 2–8 items")
        if self.template is MotionTemplate.TIMELINE:
            items = self.data["items"]
            if not isinstance(items, list) or not 2 <= len(items) <= 6:
                raise ValueError("timeline must contain 2–6 items")
        return self


class MotionRenderResult(StrictModel):
    template: MotionTemplate
    html_path: str
    video_path: str
    fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    duration_seconds: float = Field(gt=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    engine: str = "html-video-playwright-hyperframes-adapter"
