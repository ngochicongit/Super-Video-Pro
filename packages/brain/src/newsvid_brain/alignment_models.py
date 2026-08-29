from __future__ import annotations

from pydantic import Field, model_validator

from .models import StrictModel


class WordTiming(StrictModel):
    word: str = Field(min_length=1)
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    score: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def valid_interval(self) -> "WordTiming":
        if self.end <= self.start:
            raise ValueError("Word end must be greater than start")
        return self


class SceneAlignment(StrictModel):
    scene_id: str = Field(pattern=r"^scene_[0-9]{3,}$")
    audio_path: str = Field(pattern=r"^audio/scene_[0-9]{3,}\.wav$")
    text: str = Field(min_length=1)
    offset_seconds: float = Field(ge=0)
    duration_seconds: float = Field(gt=0)
    words: list[WordTiming] = Field(min_length=1)

    @model_validator(mode="after")
    def monotonic_words(self) -> "SceneAlignment":
        previous = -1.0
        for word in self.words:
            if word.start < previous or word.end > self.duration_seconds + 0.05:
                raise ValueError("Scene word timings must be monotonic and inside the audio duration")
            previous = word.end
        return self


class WordsDocument(StrictModel):
    schema_version: int = 1
    language: str = Field(default="vi", pattern=r"^vi(?:-[A-Z]{2})?$")
    provider: str = Field(min_length=1)
    fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    scenes: list[SceneAlignment] = Field(min_length=1)


class SubtitleLayout(StrictModel):
    width: int = Field(default=1080, ge=320)
    height: int = Field(default=1920, ge=320)
    top_safe_px: int = Field(default=180, ge=0)
    bottom_safe_px: int = Field(default=300, ge=0)
    max_words_per_line: int = Field(default=7, ge=1, le=12)
    max_lines: int = Field(default=2, ge=1, le=3)
    font_name: str = "Arial"
    preferred_font_size: int = Field(default=72, ge=24)
    minimum_font_size: int = Field(default=44, ge=20)
    horizontal_margin_px: int = Field(default=60, ge=20)
    outline_px: int = Field(default=4, ge=0)

    @model_validator(mode="after")
    def viable_safe_area(self) -> "SubtitleLayout":
        if self.top_safe_px + self.bottom_safe_px >= self.height:
            raise ValueError("Subtitle safe areas leave no drawable region")
        if self.minimum_font_size > self.preferred_font_size:
            raise ValueError("Minimum font size cannot exceed preferred font size")
        return self


class SubtitleReport(StrictModel):
    schema_version: int = 1
    ass_path: str = "captions/subtitles.ass"
    dialogue_count: int = Field(ge=0)
    font_size: int = Field(gt=0)
    top_safe_px: int = Field(ge=0)
    bottom_safe_px: int = Field(ge=0)
    max_words_per_line: int = Field(gt=0)
    overflow_detected: bool = False
