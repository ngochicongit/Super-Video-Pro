from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from .models import StrictModel


class ImageAsset(StrictModel):
    source_url: str
    cache_path: str = Field(pattern=r"^cache/images/[0-9a-f]{64}\.[a-z0-9]+$")
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    content_type: str = Field(pattern=r"^image/")


class TransitionType(StrEnum):
    NONE = "none"
    FADE = "fade"
    DISSOLVE = "dissolve"
    WIPELEFT = "wipeleft"
    WIPERIGHT = "wiperight"
    SLIDEUP = "slideup"


class TransitionConfig(StrictModel):
    type: TransitionType = TransitionType.FADE
    duration_seconds: float = Field(default=0.35, ge=0, le=2)

    @model_validator(mode="after")
    def consistent_duration(self) -> "TransitionConfig":
        if self.type is TransitionType.NONE and self.duration_seconds != 0:
            self.duration_seconds = 0
        if self.type is not TransitionType.NONE and self.duration_seconds <= 0:
            raise ValueError("Animated transitions require a positive duration")
        return self


class RenderedScene(StrictModel):
    scene_id: str = Field(pattern=r"^scene_[0-9]{3,}$")
    source_path: str = Field(min_length=1)
    audio_path: str = Field(pattern=r"^audio/scene_[0-9]{3,}\.wav$")
    video_path: str = Field(pattern=r"^scenes/scene_[0-9]{3,}\.mp4$")
    effect: str
    renderer: str = "ffmpeg-article-image"
    duration_seconds: float = Field(gt=0)
    fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class VideoProbe(StrictModel):
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    duration_seconds: float = Field(gt=0)
    video_codec: str = Field(min_length=1)
    audio_codec: str = Field(min_length=1)
    fps: float = Field(gt=0)


class PreviewResult(StrictModel):
    output_path: str = "output/preview.mp4"
    fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    transition: TransitionConfig
    scenes: list[RenderedScene] = Field(min_length=1)
    probe: VideoProbe


class SceneManifest(StrictModel):
    schema_version: int = 1
    fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    scenes: list[RenderedScene] = Field(min_length=1)


class RenderManifest(StrictModel):
    schema_version: int = 2
    fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    fps: int = Field(gt=0)
    output_path: str = "output/final.mp4"
    preview_path: str = "output/preview.mp4"
    scenes: list[RenderedScene] = Field(min_length=1)
    assets: list[ImageAsset] = Field(default_factory=list)
    probe: VideoProbe
    transition: TransitionConfig = Field(default_factory=TransitionConfig)
    comfyui_used: bool = False

    @model_validator(mode="after")
    def vertical_output(self) -> "RenderManifest":
        if self.height <= self.width or self.probe.height <= self.probe.width:
            raise ValueError("Final output must be vertical")
        return self
