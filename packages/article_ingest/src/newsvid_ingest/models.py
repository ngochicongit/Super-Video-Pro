from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Source(StrictModel):
    schema_version: int = 1
    url: HttpUrl
    domain: str = Field(min_length=1)
    title: str = Field(min_length=1)
    author: str | None = None
    published_at: str | None = None
    language: str | None = None
    hero_image: HttpUrl | None = None
    retrieved_at: datetime
    extraction_method: str


class ArticleImage(StrictModel):
    source_url: HttpUrl
    alt: str | None = None
    caption: str | None = None
    attribution: str | None = None
    width: int | None = Field(default=None, ge=1)
    height: int | None = Field(default=None, ge=1)
    is_hero: bool = False


class ImageManifest(StrictModel):
    schema_version: int = 1
    source_url: HttpUrl
    images: list[ArticleImage] = Field(default_factory=list)
