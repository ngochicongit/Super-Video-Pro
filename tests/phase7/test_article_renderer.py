from __future__ import annotations

import hashlib
import io
import json
import shutil
import subprocess
import wave
from pathlib import Path
from typing import Any

import httpx
import pytest

from newsvid.article_renderer import (ArticleImageCache, ArticleVideoCoordinator,
                                      FFmpegArticleRenderer)
from newsvid.checkpoint import CheckpointStore
from newsvid.persistence import atomic_write_model, atomic_write_text
from newsvid.persistence import load_model
from newsvid.project import ProjectManager
from newsvid.schemas import PipelineStage, StageStatus
from newsvid_brain import (Fact, FactSet, FactSource, ImageAsset, NewsStyle, RenderError, SceneType,
                           SourceType, Storyboard, StoryboardScene, VisualPlan,
                           VisualProvenance)
from newsvid_brain.storyboard_models import StoryboardVideo
from newsvid_brain.tts_models import AudioCacheEntry, TTSManifest
from newsvid_ingest.models import ArticleImage, ImageManifest


def make_wav(path: Path, seconds: float = 1.2, rate: int = 16000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(rate)
        stream.writeframes(b"\x00\x00" * int(seconds * rate))


def test_image_download_is_bounded_atomic_and_cached(tmp_path: Path,
                                                     monkeypatch: pytest.MonkeyPatch) -> None:
    payload = b"\x89PNG\r\nfixture"
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, request=request, content=payload,
                              headers={"content-type": "image/png"})

    monkeypatch.setattr("newsvid.article_renderer.assert_public_http_url", lambda value, **_kwargs: value)
    cache = ArticleImageCache(transport=httpx.MockTransport(handler))
    first, asset = cache.acquire("https://cdn.example/image.png", tmp_path / "cache" / "images")
    second, cached = cache.acquire("https://cdn.example/image.png", tmp_path / "cache" / "images")
    assert first == second and calls == 1
    assert first.read_bytes() == payload
    assert asset == cached and asset.sha256 == hashlib.sha256(payload).hexdigest()


def test_image_download_rejects_non_image_and_size_overflow(tmp_path: Path,
                                                            monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("newsvid.article_renderer.assert_public_http_url", lambda value, **_kwargs: value)
    html = httpx.MockTransport(lambda request: httpx.Response(
        200, request=request, content=b"html", headers={"content-type": "text/html"}))
    with pytest.raises(RenderError, match="content type"):
        ArticleImageCache(transport=html).acquire("https://cdn.example/a", tmp_path / "a")
    large = httpx.MockTransport(lambda request: httpx.Response(
        200, request=request, content=b"x" * 20, headers={"content-type": "image/jpeg"}))
    with pytest.raises(RenderError, match="size limit"):
        ArticleImageCache(max_bytes=10, transport=large).acquire("https://cdn.example/b", tmp_path / "b")


def test_ken_burns_command_adapts_crop_zoom_pan_audio_and_vertical(tmp_path: Path) -> None:
    image = tmp_path / "image.jpg"
    audio = tmp_path / "audio.wav"
    image.touch(); audio.touch()
    seen: list[str] = []

    def runner(command: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        seen.extend(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    renderer = FFmpegArticleRenderer(runner=runner)
    renderer.render_scene(image, audio, tmp_path / "scene.mp4", duration=2,
                          width=360, height=640, fps=24, effect="pan_right")
    vf = seen[seen.index("-vf") + 1]
    assert "scale=720:1280:force_original_aspect_ratio=increase" in vf
    assert "crop=720:1280" in vf and "zoompan=" in vf and "s=360x640" in vf
    assert "-c:a" in seen and "aac" in seen and "-shortest" in seen
    assert seen[0] == "ffmpeg"


def seed_render_project(tmp_path: Path, ffmpeg: str) -> tuple[ProjectManager, str]:
    manager = ProjectManager(tmp_path / "projects")
    project = manager.create("Bản tin ảnh bài viết")
    directory = manager.project_dir(project.id)
    atomic_write_text(directory / "article.md", "# Tin công nghệ\n\nMột sự kiện có thật.")
    atomic_write_text(directory / "script.json", '{"language":"vi","segments":[]}')
    atomic_write_model(directory / "facts.json", FactSet(
        source=FactSource(url="https://news.example.vn/article", publisher="News",
                          title="Tin công nghệ"),
        facts=[Fact(id="fact_001", claim="Một sự kiện có thật.",
                    evidence="Một sự kiện có thật.", importance=1, confidence=1)]))
    source_url = "https://news.example.vn/media/hero.png"
    image = directory / "cache" / "images" / (hashlib.sha256(source_url.encode()).hexdigest() + ".png")
    image.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([ffmpeg, "-y", "-f", "lavfi", "-i", "color=c=0x176B87:s=800x450",
                    "-frames:v", "1", str(image)], check=True, capture_output=True, shell=False)
    asset = ImageAsset(source_url=source_url, cache_path=f"cache/images/{image.name}",
                       sha256=hashlib.sha256(image.read_bytes()).hexdigest(), content_type="image/png")
    url_key = hashlib.sha256(source_url.encode()).hexdigest()
    atomic_write_model(image.parent / f"{url_key}.json", asset)
    atomic_write_model(directory / "images.json", ImageManifest(
        source_url="https://news.example.vn/article",
        images=[ArticleImage(source_url=source_url, is_hero=True, width=800, height=450)]))
    visual = VisualPlan(type=SceneType.ARTICLE_IMAGE, template="article-photo",
                        provenance=VisualProvenance(source_type=SourceType.ARTICLE,
                                                    source_url=source_url))
    atomic_write_model(directory / "storyboard.json", Storyboard(
        video=StoryboardVideo(width=360, height=640, fps=15, target_duration=30,
                              style=NewsStyle.TECH_NEWS),
        scenes=[StoryboardScene(id="scene_001", script_segment_id="segment_001",
                                type=SceneType.ARTICLE_IMAGE, narration="Tin mới Việt Nam.",
                                fact_refs=["fact_001"], duration_seconds=1.2, visual=visual)]))
    audio = directory / "audio" / "scene_001.wav"
    make_wav(audio)
    atomic_write_model(directory / "audio" / "tts_manifest.json", TTSManifest(
        provider="fixture", voice="vi", provider_config_fingerprint="fixture",
        pronunciation_fingerprint="a" * 64,
        entries=[AudioCacheEntry(scene_id="scene_001", relative_path="audio/scene_001.wav",
                                 fingerprint="sha256:" + "b" * 64,
                                 audio_sha256=hashlib.sha256(audio.read_bytes()).hexdigest(),
                                 normalized_text="Tin mới Việt Nam.", duration_seconds=1.2)]))
    ass = """[Script Info]
ScriptType: v4.00+
PlayResX: 360
PlayResY: 640
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: NewsVi,Arial,32,&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,2,1,2,20,20,100,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:01.10,NewsVi,,0,0,0,,{\\an2}{\\k30}Tin {\\k30}mới {\\k30}Việt {\\k20}Nam.
"""
    atomic_write_text(directory / "captions" / "subtitles.ass", ass)
    return manager, project.id


@pytest.mark.acceptance
def test_actual_article_asset_vertical_mp4_render_without_comfyui(tmp_path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        pytest.skip("FFmpeg/FFprobe unavailable")
    manager, project_id = seed_render_project(tmp_path, ffmpeg)
    coordinator = ArticleVideoCoordinator(manager, ArticleImageCache(),
                                          FFmpegArticleRenderer(ffmpeg=ffmpeg, ffprobe=ffprobe))
    result = coordinator.render(project_id)
    cached = coordinator.render(project_id)
    directory = manager.project_dir(project_id)
    output = directory / result.output_path
    assert output.is_file() and output.stat().st_size > 5_000
    assert result.probe.width == 360 and result.probe.height == 640
    assert result.probe.video_codec == "h264" and result.probe.audio_codec == "aac"
    assert 1.0 <= result.probe.duration_seconds <= 1.5
    assert result.comfyui_used is False and cached == result
    assert (directory / "output" / "article-video.preview.mp4").is_file()
    checkpoint = CheckpointStore(directory / "checkpoint.json").load()
    assert checkpoint.stages[PipelineStage.VISUALS].status is StageStatus.COMPLETED
    assert checkpoint.stages[PipelineStage.SCENES].status is StageStatus.COMPLETED
    assert checkpoint.stages[PipelineStage.PREVIEW].status is StageStatus.COMPLETED
    assert checkpoint.stages[PipelineStage.FINAL_RENDER].status is StageStatus.COMPLETED


def test_renderer_rejects_unresolved_factual_scene_before_ffmpeg(tmp_path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        pytest.skip("FFmpeg/FFprobe unavailable")
    manager, project_id = seed_render_project(tmp_path, ffmpeg)
    directory = manager.project_dir(project_id)
    board = load_model(directory / "storyboard.json", Storyboard)
    board.scenes[0].fact_refs = ["fact_999"]
    atomic_write_model(directory / "storyboard.json", board)
    with pytest.raises(RenderError, match="unresolved fact"):
        ArticleVideoCoordinator(manager, ArticleImageCache(),
                                FFmpegArticleRenderer(ffmpeg=ffmpeg, ffprobe=ffprobe)).render(project_id)
    assert not (directory / "output" / "article-video.mp4").exists()
