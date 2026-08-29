from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from .models import StrictModel
from .storyboard_models import SourceType, VisualProvenance


class ComfyUIWorkflow(StrEnum):
    NEWS_IMAGE = "news-image"
    BACKGROUND = "background"
    INFOGRAPHIC = "infographic"


class VisualGenerationRequest(StrictModel):
    scene_id: str = Field(pattern=r"^scene_[0-9]{3,}$")
    workflow: ComfyUIWorkflow
    prompt: str = Field(min_length=1, max_length=4000)
    negative_prompt: str = "blurry, low quality, distorted, watermark, illegible text"
    width: int = Field(default=768, ge=256, le=2048)
    height: int = Field(default=1344, ge=256, le=2048)
    seed: int = Field(ge=0, le=2**63 - 1)
    steps: int = Field(default=20, ge=1, le=100)
    cfg: float = Field(default=7.0, ge=0, le=30)

    @model_validator(mode="after")
    def latent_dimensions(self) -> "VisualGenerationRequest":
        if self.width % 8 or self.height % 8:
            raise ValueError("ComfyUI image dimensions must be divisible by 8")
        return self


class QueuedPrompt(StrictModel):
    prompt_id: str = Field(min_length=1)
    client_id: str = Field(min_length=1)


class ComfyUIOutput(StrictModel):
    filename: str = Field(min_length=1)
    subfolder: str = ""
    type: str = "output"
    content: bytes = Field(min_length=1, exclude=True)


class GeneratedVisualAsset(StrictModel):
    scene_id: str = Field(pattern=r"^scene_[0-9]{3,}$")
    workflow: ComfyUIWorkflow
    relative_path: str = Field(min_length=1)
    fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    prompt_id: str = Field(min_length=1)
    provenance: VisualProvenance

    @model_validator(mode="after")
    def generated_provenance(self) -> "GeneratedVisualAsset":
        if self.provenance.source_type is not SourceType.GENERATED:
            raise ValueError("ComfyUI assets require generated provenance")
        if self.provenance.generator != "comfyui" or self.provenance.workflow != self.workflow.value:
            raise ValueError("ComfyUI asset provenance does not match its workflow")
        return self


class VisualFailure(StrictModel):
    scene_id: str = Field(pattern=r"^scene_[0-9]{3,}$")
    workflow: ComfyUIWorkflow
    error: str = Field(min_length=1, max_length=1000)


class VisualManifest(StrictModel):
    schema_version: int = 1
    provider: str = "comfyui"
    assets: list[GeneratedVisualAsset] = Field(default_factory=list)
    failures: list[VisualFailure] = Field(default_factory=list)
