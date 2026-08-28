from __future__ import annotations

from pydantic import Field, model_validator

from .models import StrictModel


class ImageAsset(StrictModel):
    source_url: str
    cache_path: str = Field(pattern=r"^cache/images/[0-9a-f]{64}\.[a-z0-9]+$")
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    content_type: str = Field(pattern=r"^image/")


class RenderedScene(StrictModel):
    scene_id: str = Field(pattern=r"^scene_[0-9]{3,}$")
    image_path: str
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


class RenderManifest(StrictModel):
    schema_version: int = 1
    fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    fps: int = Field(gt=0)
    output_path: str = "output/article-video.mp4"
    scenes: list[RenderedScene] = Field(min_length=1)
    assets: list[ImageAsset] = Field(min_length=1)
    probe: VideoProbe
    comfyui_used: bool = False

    @model_validator(mode="after")
    def vertical_output(self) -> "RenderManifest":
        if self.height <= self.width or self.probe.height <= self.probe.width:
            raise ValueError("Article-asset output must be vertical")
        if self.comfyui_used:
            raise ValueError("Phase 7 renderer cannot use ComfyUI")
        return self
