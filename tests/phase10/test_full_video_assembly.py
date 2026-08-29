from __future__ import annotations

import hashlib
import shutil
import subprocess
import wave
from pathlib import Path
from typing import Any

import pytest

from newsvid.article_renderer import ArticleImageCache, FFmpegArticleRenderer
from newsvid.checkpoint import CheckpointStore
from newsvid.final_assembler import FinalAssembler
from newsvid.motion_renderer import HyperFramesChromiumRenderer, SceneRenderer
from newsvid.persistence import atomic_write_model, atomic_write_text
from newsvid.project import ProjectManager
from newsvid.schemas import PipelineStage, StageStatus
from newsvid.video_renderer import VideoRenderCoordinator
from newsvid_brain import (Fact, FactSet, FactSource, GeneratedVisualAsset, ImageAsset,
                           NewsStyle, RenderedScene, SceneType, SourceType, Storyboard,
                           StoryboardScene, TransitionConfig, TransitionType,
                           VisualManifest, VisualPlan, VisualProvenance)
from newsvid_brain.storyboard_models import StoryboardVideo
from newsvid_brain.tts_models import AudioCacheEntry, TTSManifest
from newsvid_ingest.models import ArticleImage, ImageManifest

EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")


def rendered(index: int, duration: float = 2) -> RenderedScene:
    return RenderedScene(
        scene_id=f"scene_{index:03d}", source_path="motion-generated",
        audio_path=f"audio/scene_{index:03d}.wav",
        video_path=f"scenes/scene_{index:03d}.mp4", effect="zoom_in",
        renderer="fixture", duration_seconds=duration,
        fingerprint="sha256:" + f"{index:064x}",
    )


def test_filter_graph_normalizes_mixed_scenes_and_chains_transitions() -> None:
    graph, video, audio = FinalAssembler._filter_graph(
        [rendered(1, 2), rendered(2, 3), rendered(3, 4)],
        TransitionConfig(type=TransitionType.DISSOLVE, duration_seconds=.5),
        width=1080, height=1920, fps=30,
    )
    assert graph.count("settb=AVTB,setpts=PTS-STARTPTS,fps=30") == 3
    assert graph.count("aresample=48000") == 3
    assert "xfade=transition=dissolve:duration=0.500:offset=1.500" in graph
    assert "xfade=transition=dissolve:duration=0.500:offset=4.000" in graph
    assert graph.count("acrossfade=d=0.500") == 2
    assert (video, audio) == ("[vout]", "[aout]")


def test_hard_cut_uses_normalized_concat_filter() -> None:
    graph, video, audio = FinalAssembler._filter_graph(
        [rendered(1), rendered(2)],
        TransitionConfig(type=TransitionType.NONE, duration_seconds=0),
        width=1080, height=1920, fps=30,
    )
    assert "[v0][a0][v1][a1]concat=n=2:v=1:a=1[vout][aout]" in graph
    assert (video, audio) == ("[vout]", "[aout]")


def test_assembler_command_enforces_final_codecs_and_dimensions(tmp_path: Path) -> None:
    scenes = [rendered(1), rendered(2)]
    for item in scenes:
        path = tmp_path / item.video_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    seen: list[str] = []

    def runner(command: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        seen.extend(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    FinalAssembler(runner=runner).assemble_preview(
        scenes, tmp_path, tmp_path / "output" / "preview.mp4",
        transition=TransitionConfig(), width=1080, height=1920, fps=30,
    )
    graph = seen[seen.index("-filter_complex") + 1]
    assert "scale=1080:1920" in graph and "pad=1080:1920" in graph
    assert seen[seen.index("-c:v") + 1] == "libx264"
    assert seen[seen.index("-c:a") + 1] == "aac"
    assert seen[seen.index("-pix_fmt") + 1] == "yuv420p"
    assert seen[seen.index("-r") + 1] == "30"


def test_transition_retimes_later_ass_dialogue(tmp_path: Path) -> None:
    source = tmp_path / "subtitles.ass"
    output = tmp_path / "subtitles.final.ass"
    atomic_write_text(source, """[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.20,0:00:01.80,NewsVi,,0,0,0,,Một
Dialogue: 0,0:00:02.00,0:00:03.50,NewsVi,,0,0,0,,Hai
Dialogue: 0,0:00:05.00,0:00:06.00,NewsVi,,0,0,0,,Ba""")
    FinalAssembler._retime_ass(source, output,
                               [rendered(1, 2), rendered(2, 3), rendered(3, 2)], .5)
    text = output.read_text(encoding="utf-8")
    assert "0:00:00.20,0:00:01.80" in text
    assert "0:00:01.50,0:00:03.00" in text
    assert "0:00:04.00,0:00:05.00" in text


def wav(path: Path, seconds: float = .8) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(16000)
        stream.writeframes(b"\x00\x00" * int(16000 * seconds))


def make_image(ffmpeg: str, path: Path, color: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([ffmpeg, "-y", "-f", "lavfi", "-i", f"color=c={color}:s=900x1600",
                    "-frames:v", "1", str(path)], check=True, capture_output=True, shell=False)


def seed_full_project(tmp_path: Path, ffmpeg: str) -> tuple[ProjectManager, str]:
    manager = ProjectManager(tmp_path / "projects")
    project = manager.create("Phase 10 full assembly")
    directory = manager.project_dir(project.id)
    facts = FactSet(
        source=FactSource(url="https://news.example.vn/phase10", publisher="News", title="Tin AI"),
        facts=[Fact(id="fact_001", claim="Một nền tảng AI được công bố.",
                    evidence="Một nền tảng AI được công bố.", importance=1, confidence=1)],
    )
    atomic_write_model(directory / "facts.json", facts)

    article_url = "https://news.example.vn/article.jpg"
    url_key = hashlib.sha256(article_url.encode()).hexdigest()
    article_path = directory / "cache" / "images" / f"{url_key}.png"
    make_image(ffmpeg, article_path, "0x176B87")
    article_asset = ImageAsset(source_url=article_url,
                               cache_path=f"cache/images/{article_path.name}",
                               sha256=hashlib.sha256(article_path.read_bytes()).hexdigest(),
                               content_type="image/png")
    atomic_write_model(article_path.with_suffix(".json"), article_asset)
    atomic_write_model(directory / "images.json", ImageManifest(
        source_url="https://news.example.vn/phase10",
        images=[ArticleImage(source_url=article_url, is_hero=True, width=900, height=1600)]))

    generated_path = directory / "images" / "generated" / "scene_003-fixture.png"
    make_image(ffmpeg, generated_path, "0x6B46C1")
    generated_sha = hashlib.sha256(generated_path.read_bytes()).hexdigest()
    generated = GeneratedVisualAsset(
        scene_id="scene_003", workflow="news-image",
        relative_path="images/generated/scene_003-fixture.png",
        fingerprint="sha256:" + "c" * 64, content_sha256=generated_sha,
        prompt_id="fixture-job",
        provenance=VisualProvenance(source_type=SourceType.GENERATED,
                                    local_path="images/generated/scene_003-fixture.png",
                                    generator="comfyui", workflow="news-image"),
    )
    atomic_write_model(directory / "images" / "generated_manifest.json",
                       VisualManifest(assets=[generated]))

    scenes = [
        StoryboardScene(
            id="scene_001", script_segment_id="segment_001", type=SceneType.ARTICLE_IMAGE,
            narration="Một nền tảng AI được công bố.", fact_refs=["fact_001"],
            duration_seconds=.8,
            visual=VisualPlan(type=SceneType.ARTICLE_IMAGE, template="article-source-image",
                              provenance=VisualProvenance(source_type=SourceType.ARTICLE,
                                                          source_url=article_url))),
        StoryboardScene(
            id="scene_002", script_segment_id="segment_002", type=SceneType.STAT_HERO,
            narration="Tỷ lệ thử nghiệm đạt 75 phần trăm.", fact_refs=["fact_001"],
            duration_seconds=.8,
            visual=VisualPlan(type=SceneType.STAT_HERO, template="frame-pentagram-stat",
                              provenance=VisualProvenance(source_type=SourceType.GRAPHIC),
                              data={"value": "75%", "label": "Thử nghiệm"})),
        StoryboardScene(
            id="scene_003", script_segment_id="segment_003", type=SceneType.AI_ILLUSTRATION,
            narration="Minh họa cho khái niệm công nghệ.", fact_refs=["fact_001"],
            duration_seconds=.8,
            visual=VisualPlan(type=SceneType.AI_ILLUSTRATION, template="news-ai-illustration",
                              provenance=generated.provenance,
                              prompt="Minh họa công nghệ trung tính")),
    ]
    atomic_write_model(directory / "storyboard.json", Storyboard(
        video=StoryboardVideo(width=1080, height=1920, fps=30, target_duration=30,
                              style=NewsStyle.TECH_NEWS), scenes=scenes))

    entries: list[AudioCacheEntry] = []
    for scene in scenes:
        audio = directory / "audio" / f"{scene.id}.wav"
        wav(audio)
        entries.append(AudioCacheEntry(
            scene_id=scene.id, relative_path=f"audio/{scene.id}.wav",
            fingerprint="sha256:" + hashlib.sha256(scene.id.encode()).hexdigest(),
            audio_sha256=hashlib.sha256(audio.read_bytes()).hexdigest(),
            normalized_text=scene.narration, duration_seconds=.8,
        ))
    atomic_write_model(directory / "audio" / "tts_manifest.json", TTSManifest(
        provider="fixture", voice="vi", provider_config_fingerprint="fixture",
        pronunciation_fingerprint="d" * 64, entries=entries))
    atomic_write_text(directory / "captions" / "subtitles.ass", """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: NewsVi,Arial,64,&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,40,40,300,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:00.70,NewsVi,,0,0,0,,{\\an2}Tin bài viết
Dialogue: 0,0:00:00.80,0:00:01.50,NewsVi,,0,0,0,,{\\an2}Đồ họa chuyển động
Dialogue: 0,0:00:01.60,0:00:02.30,NewsVi,,0,0,0,,{\\an2}Ảnh AI
""")
    return manager, project.id


@pytest.mark.acceptance
def test_real_full_1080x1920_video_with_image_motion_ai_voice_captions_and_transition(
        tmp_path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe or not EDGE.is_file():
        pytest.skip("FFmpeg/FFprobe/Edge unavailable")
    manager, project_id = seed_full_project(tmp_path, ffmpeg)
    article = FFmpegArticleRenderer(ffmpeg=ffmpeg, ffprobe=ffprobe)
    motion = HyperFramesChromiumRenderer(repository_root=Path.cwd(), ffmpeg=ffmpeg,
                                         chromium=EDGE)
    coordinator = VideoRenderCoordinator(
        manager, ArticleImageCache(), SceneRenderer(article, motion),
        FinalAssembler(ffmpeg=ffmpeg, ffprobe=ffprobe),
    )
    transition = TransitionConfig(type=TransitionType.DISSOLVE, duration_seconds=.2)
    preview = coordinator.preview(project_id, transition=transition)
    result = coordinator.render(project_id, transition=transition)
    cached = coordinator.render(project_id, transition=transition)
    directory = manager.project_dir(project_id)
    assert (directory / preview.output_path).stat().st_size > 10_000
    assert (directory / result.output_path).stat().st_size > 10_000
    assert (result.probe.width, result.probe.height, result.probe.fps) == (1080, 1920, 30)
    assert (result.probe.video_codec, result.probe.audio_codec) == ("h264", "aac")
    assert 1.7 <= result.probe.duration_seconds <= 2.2
    assert {scene.renderer for scene in result.scenes} == {
        "ffmpeg-article-image", "html-video-playwright-hyperframes-adapter", "ffmpeg-ai-image"
    }
    assert result.comfyui_used is True and result.transition == transition and cached == result
    assert (directory / "captions" / "subtitles.final.ass").is_file()
    checkpoint = CheckpointStore(directory / "checkpoint.json").load()
    assert checkpoint.stages[PipelineStage.SCENES].status is StageStatus.COMPLETED
    assert checkpoint.stages[PipelineStage.PREVIEW].status is StageStatus.COMPLETED
    assert checkpoint.stages[PipelineStage.FINAL_RENDER].status is StageStatus.COMPLETED


@pytest.mark.acceptance
def test_scene_render_preserves_unrelated_outputs_and_no_change_is_a_real_cache_hit(
        tmp_path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe or not EDGE.is_file():
        pytest.skip("FFmpeg/FFprobe/Edge unavailable")
    manager, project_id = seed_full_project(tmp_path, ffmpeg)
    coordinator = VideoRenderCoordinator(
        manager, ArticleImageCache(),
        SceneRenderer(
            FFmpegArticleRenderer(ffmpeg=ffmpeg, ffprobe=ffprobe),
            HyperFramesChromiumRenderer(repository_root=Path.cwd(), ffmpeg=ffmpeg,
                                         chromium=EDGE),
        ),
        FinalAssembler(ffmpeg=ffmpeg, ffprobe=ffprobe),
    )
    coordinator.preview(project_id, transition=TransitionConfig())
    directory = manager.project_dir(project_id)
    paths = {scene_id: directory / "scenes" / f"{scene_id}.mp4"
             for scene_id in ("scene_001", "scene_002", "scene_003")}
    before = {scene_id: (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns)
              for scene_id, path in paths.items()}

    storyboard_path = directory / "storyboard.json"
    storyboard = Storyboard.model_validate_json(storyboard_path.read_text(encoding="utf-8"))
    changed = storyboard.model_copy(deep=True)
    changed.scenes[1].visual.template = "frame-pentagram-stat-selective"
    atomic_write_model(storyboard_path, changed)
    rendered = coordinator.render_scene(project_id, "scene_002")
    after = {scene_id: (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns)
             for scene_id, path in paths.items()}
    assert rendered.scene_id == "scene_002"
    assert after["scene_002"] != before["scene_002"]
    assert after["scene_001"] == before["scene_001"]
    assert after["scene_003"] == before["scene_003"]

    coordinator.render_scene(project_id, "scene_002")
    cached = {scene_id: (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns)
              for scene_id, path in paths.items()}
    assert cached == after
