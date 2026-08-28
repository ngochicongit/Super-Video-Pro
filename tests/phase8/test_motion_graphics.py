from __future__ import annotations

import io
import json
import shutil
import subprocess
import wave
from pathlib import Path

import pytest

from newsvid.article_renderer import FFmpegArticleRenderer
from newsvid.final_assembler import FinalAssembler
from newsvid.motion_renderer import (HyperFramesChromiumRenderer, SceneRenderer,
                                     motion_input_for_scene)
from newsvid_brain import (MotionTemplate, MotionTemplateInput, SceneType,
                           SourceType, StoryboardScene, VisualPlan,
                           VisualProvenance)
from newsvid_brain.motion_templates import render_motion_html


ROOT = Path(__file__).parents[2]
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")

CASES = {
    MotionTemplate.HOOK: {"headline": "TIN MỚI", "subhead": "Việt Nam"},
    MotionTemplate.HEADLINE: {"headline": "Tiêu điểm công nghệ"},
    MotionTemplate.STAT_HERO: {"value": "75%", "label": "Tăng trưởng"},
    MotionTemplate.CHART: {"title": "Thị phần", "data": [
        {"label": "A", "value": 20}, {"label": "B", "value": 55}]},
    MotionTemplate.COMPARISON: {"left": {"label": "Trước", "value": "10%"},
                                "right": {"label": "Sau", "value": "25%"}},
    MotionTemplate.TIMELINE: {"items": [
        {"label": "2025", "text": "Khởi động"}, {"label": "2026", "text": "Ra mắt"}]},
    MotionTemplate.QUOTE: {"quote": "Dữ liệu phải chính xác.", "author": "Nguồn bài viết"},
    MotionTemplate.OUTRO: {"headline": "Cảm ơn bạn đã theo dõi", "source": "Super Video Pro"},
}


@pytest.mark.parametrize(("template", "data"), CASES.items())
def test_eight_templates_accept_structured_input_and_escape_html(template: MotionTemplate,
                                                                 data: dict[str, object]) -> None:
    payload = dict(data)
    if template in {MotionTemplate.HOOK, MotionTemplate.HEADLINE, MotionTemplate.OUTRO}:
        payload["headline"] = str(payload["headline"]) + " <script>bad()</script>"
    spec = MotionTemplateInput(template=template, duration_seconds=1, data=payload)
    html = render_motion_html(spec, "/* gsap fixture */")
    assert f'data-template="{template.value}"' in html
    assert "<script>bad()</script>" not in html
    assert "window.__newsvidPlay" in html and "gsap.timeline" in html
    assert "width:1080px" in html and "height:1920px" in html


def test_template_schema_rejects_missing_or_invalid_data() -> None:
    with pytest.raises(ValueError, match="requires"):
        MotionTemplateInput(template="stat-hero", duration_seconds=1, data={"value": "20%"})
    with pytest.raises(ValueError, match="2–8"):
        MotionTemplateInput(template="chart", duration_seconds=1,
                            data={"title": "X", "data": [{"label": "A", "value": 1}]})


def runtime() -> HyperFramesChromiumRenderer:
    return HyperFramesChromiumRenderer(repository_root=ROOT, chromium=EDGE)


@pytest.mark.acceptance
@pytest.mark.parametrize(("template", "data"), CASES.items())
def test_every_template_renders_independently_in_chromium(template: MotionTemplate,
                                                          data: dict[str, object],
                                                          tmp_path: Path) -> None:
    if not EDGE.is_file() or not shutil.which("ffmpeg"):
        pytest.skip("Edge/FFmpeg unavailable")
    spec = MotionTemplateInput(template=template, duration_seconds=.35,
                               width=320, height=568, fps=10, data=data)
    result = runtime().render(spec, tmp_path / f"{template.value}.html",
                              tmp_path / f"{template.value}.mp4")
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                            "stream=codec_name,width,height", "-of", "json", result.video_path],
                           check=True, capture_output=True, text=True, shell=False)
    stream = json.loads(probe.stdout)["streams"][0]
    assert stream == {"codec_name": "h264", "width": 320, "height": 568}
    assert Path(result.video_path).stat().st_size > 1_000


def wav(path: Path, seconds: float = .6) -> None:
    with wave.open(str(path), "wb") as stream:
        stream.setnchannels(1); stream.setsampwidth(2); stream.setframerate(16000)
        stream.writeframes(b"\x00\x00" * int(16000 * seconds))


@pytest.mark.acceptance
def test_scene_renderer_integrates_motion_video_with_audio_and_ffmpeg(tmp_path: Path) -> None:
    if not EDGE.is_file() or not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("Edge/FFmpeg unavailable")
    scene = StoryboardScene(
        id="scene_001", script_segment_id="segment_001", type=SceneType.STAT_HERO,
        narration="Tỷ lệ tăng 75 phần trăm.", fact_refs=["fact_001"], duration_seconds=.6,
        visual=VisualPlan(type=SceneType.STAT_HERO, template="frame-pentagram-stat",
                          provenance=VisualProvenance(source_type=SourceType.GRAPHIC),
                          data={"value": "75%", "label": "Tăng trưởng"}),
    )
    audio = tmp_path / "voice.wav"; wav(audio)
    output = tmp_path / "scene.mp4"
    ffmpeg_renderer = FFmpegArticleRenderer()
    engine = SceneRenderer(ffmpeg_renderer, runtime()).render(
        scene, image=None, audio=audio, output=output, width=320, height=568,
        fps=10, duration=.6, fingerprint="sha256:" + "a" * 64,
        source_path="motion-generated", audio_path="audio/scene_001.wav")
    probe = FinalAssembler().probe(output)
    assert engine.renderer == "html-video-playwright-hyperframes-adapter"
    assert (probe.width, probe.height, probe.video_codec, probe.audio_codec) == (320, 568, "h264", "aac")
    assert .5 <= probe.duration_seconds <= .8


@pytest.mark.acceptance
def test_motion_runtime_outputs_native_1080x1920_mp4(tmp_path: Path) -> None:
    if not EDGE.is_file() or not shutil.which("ffmpeg"):
        pytest.skip("Edge/FFmpeg unavailable")
    spec = MotionTemplateInput(template=MotionTemplate.HOOK, duration_seconds=.35,
                               width=1080, height=1920, fps=15,
                               data={"headline": "TIN CÔNG NGHỆ", "subhead": "Việt Nam"})
    result = runtime().render(spec, tmp_path / "hook-vertical.html", tmp_path / "hook-vertical.mp4")
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=width,height",
                            "-of", "json", result.video_path], check=True, capture_output=True,
                           text=True, shell=False)
    assert json.loads(probe.stdout)["streams"][0] == {"width": 1080, "height": 1920}


def test_storyboard_scene_mapping_covers_all_phase8_templates() -> None:
    mapping = {
        SceneType.HOOK: MotionTemplate.HOOK, SceneType.HEADLINE: MotionTemplate.HEADLINE,
        SceneType.STAT_HERO: MotionTemplate.STAT_HERO, SceneType.CHART: MotionTemplate.CHART,
        SceneType.COMPARISON: MotionTemplate.COMPARISON, SceneType.TIMELINE: MotionTemplate.TIMELINE,
        SceneType.QUOTE: MotionTemplate.QUOTE, SceneType.OUTRO: MotionTemplate.OUTRO,
    }
    for scene_type, expected in mapping.items():
        data = CASES[expected]
        scene = StoryboardScene(
            id="scene_001", script_segment_id="segment_001", type=scene_type,
            narration="Nội dung bản tin.", fact_refs=["fact_001"], duration_seconds=1,
            visual=VisualPlan(type=scene_type, template=expected.value,
                              provenance=VisualProvenance(source_type=SourceType.GRAPHIC), data=data),
        )
        assert motion_input_for_scene(scene, width=1080, height=1920, fps=30,
                                      duration=1).template is expected
