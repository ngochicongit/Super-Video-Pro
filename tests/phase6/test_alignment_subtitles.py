from __future__ import annotations

import io
import json
import shutil
import subprocess
import wave
from pathlib import Path
from typing import Any

import httpx
import pytest

from newsvid.alignment import AlignmentCoordinator
from newsvid.checkpoint import CheckpointStore
from newsvid.persistence import atomic_write_model
from newsvid.project import ProjectManager
from newsvid.schemas import PipelineStage, StageStatus
from newsvid_brain import (AlignmentError, SceneAlignment, SubtitleLayout,
                           WhisperXConfig, WhisperXProvider, WordTiming,
                           WordsDocument, generate_ass)
from newsvid_brain.storyboard_models import (SceneType, SourceType, Storyboard,
                                             StoryboardScene, StoryboardVideo,
                                             VisualPlan, VisualProvenance)
from newsvid_brain.script_models import NewsStyle
from newsvid_brain.tts_models import AudioCacheEntry, TTSManifest


def wav_bytes(seconds: float = 3.0, rate: int = 16000) -> bytes:
    target = io.BytesIO()
    with wave.open(target, "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(rate)
        stream.writeframes(b"\x00\x00" * int(seconds * rate))
    return target.getvalue()


def timings(*tokens: str, step: float = 0.3) -> list[WordTiming]:
    return [WordTiming(word=token, start=index * step, end=(index + 1) * step)
            for index, token in enumerate(tokens)]


def test_whisperx_posts_vietnamese_alignment_request(tmp_path: Path) -> None:
    audio = tmp_path / "speech.wav"
    audio.write_bytes(wav_bytes())
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = request.content
        return httpx.Response(200, request=request, json={"words": [
            {"word": "Xin", "start": 0.0, "end": 0.3, "score": 0.98},
            {"word": "chào", "start": 0.3, "end": 0.7, "score": 0.97},
        ]})

    provider = WhisperXProvider(WhisperXConfig(max_attempts=1),
                                transport=httpx.MockTransport(handler))
    words = provider.align(audio, "Xin chào", language="vi")
    assert [word.word for word in words] == ["Xin", "chào"]
    assert b'name="language"' in seen["body"] and b"vi" in seen["body"]
    assert b'name="text"' in seen["body"] and "Xin chào".encode() in seen["body"]


def test_whisperx_is_loopback_only_and_invalid_output_is_safe(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="loopback"):
        WhisperXProvider(WhisperXConfig(base_url="https://align.example.com"))
    audio = tmp_path / "speech.wav"
    audio.write_bytes(wav_bytes())
    provider = WhisperXProvider(WhisperXConfig(max_attempts=1),
        transport=httpx.MockTransport(lambda request: httpx.Response(200, request=request,
                                                                     json={"segments": []})))
    with pytest.raises(AlignmentError, match="no word timestamp"):
        provider.align(audio, "Xin chào")


def test_videogen_ass_behaviour_ported_with_karaoke_and_offset() -> None:
    document = WordsDocument(provider="fixture", fingerprint="sha256:" + "a" * 64,
        scenes=[SceneAlignment(scene_id="scene_001", audio_path="audio/scene_001.wav",
                               text="Xin chào Việt Nam", offset_seconds=10,
                               duration_seconds=2, words=timings("Xin", "chào", "Việt", "Nam"))])
    ass, report = generate_ass(document, SubtitleLayout())
    assert ass.startswith("[Script Info]")
    assert "0:00:10.00" in ass
    assert r"{\k30}Xin" in ass
    assert r"{\an2}" in ass
    assert "Việt Nam" not in ass  # karaoke tags remain word-level
    assert report.dialogue_count == 1


def test_caption_splitting_prefers_seven_words_and_punctuation() -> None:
    words = timings("Một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín.", "Mười")
    document = WordsDocument(provider="fixture", fingerprint="sha256:" + "b" * 64,
        scenes=[SceneAlignment(scene_id="scene_001", audio_path="audio/scene_001.wav",
                               text="Bản tin", offset_seconds=0, duration_seconds=4, words=words)])
    ass, report = generate_ass(document, SubtitleLayout(max_words_per_line=7))
    assert ass.count("Dialogue:") == 3
    assert report.max_words_per_line == 7


def test_safe_areas_are_encoded_and_overflow_is_rejected() -> None:
    document = WordsDocument(provider="fixture", fingerprint="sha256:" + "c" * 64,
        scenes=[SceneAlignment(scene_id="scene_001", audio_path="audio/scene_001.wav",
                               text="Tin", offset_seconds=0, duration_seconds=2,
                               words=timings("Tin", "mới"))])
    ass, report = generate_ass(document, SubtitleLayout(top_safe_px=180, bottom_safe_px=300))
    assert ",300,1" in ass
    assert report.top_safe_px == 180 and report.bottom_safe_px == 300
    huge = WordsDocument(provider="fixture", fingerprint="sha256:" + "d" * 64,
        scenes=[SceneAlignment(scene_id="scene_001", audio_path="audio/scene_001.wav",
                               text="Dài", offset_seconds=0, duration_seconds=2,
                               words=timings("W" * 200))])
    with pytest.raises(AlignmentError, match="overflow"):
        generate_ass(huge, SubtitleLayout())


def test_generated_ass_is_accepted_by_ffmpeg_libass(tmp_path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        pytest.skip("FFmpeg is unavailable")
    document = WordsDocument(provider="fixture", fingerprint="sha256:" + "f" * 64,
        scenes=[SceneAlignment(scene_id="scene_001", audio_path="audio/scene_001.wav",
                               text="Bản tin Việt Nam", offset_seconds=0,
                               duration_seconds=1.5,
                               words=timings("Bản", "tin", "Việt", "Nam"))])
    ass, _ = generate_ass(document, SubtitleLayout())
    (tmp_path / "captions.ass").write_text(ass, encoding="utf-8")
    result = subprocess.run(
        [ffmpeg, "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
         "color=c=black:s=1080x1920:d=1.5", "-vf", "ass=captions.ass",
         "-frames:v", "1", "-f", "null", "-"],
        cwd=tmp_path, capture_output=True, text=True, shell=False, timeout=30,
    )
    assert result.returncode == 0, result.stderr


class FakeAlignmentProvider:
    name = "fixture-aligner"
    cache_key = "fixture-v1"

    def __init__(self) -> None:
        self.calls = 0

    def align(self, audio_path: Path, text: str, *, language: str = "vi") -> list[WordTiming]:
        assert audio_path.is_file() and language == "vi"
        self.calls += 1
        tokens = text.split()
        return timings(*tokens, step=2.5 / len(tokens))


def project_with_audio(tmp_path: Path) -> tuple[ProjectManager, str]:
    manager = ProjectManager(tmp_path / "projects")
    project = manager.create("Subtitle test")
    directory = manager.project_dir(project.id)
    visual = VisualPlan(type=SceneType.KINETIC_TEXT, template="kinetic",
                        provenance=VisualProvenance(source_type=SourceType.GRAPHIC))
    board = Storyboard(video=StoryboardVideo(target_duration=60, style=NewsStyle.TECH_NEWS),
        scenes=[StoryboardScene(id="scene_001", script_segment_id="segment_001",
                                type=SceneType.KINETIC_TEXT, narration="Xin chào Việt Nam",
                                fact_refs=["fact_001"], duration_seconds=3, visual=visual)])
    atomic_write_model(directory / "storyboard.json", board)
    audio = directory / "audio" / "scene_001.wav"
    audio.write_bytes(wav_bytes())
    import hashlib
    manifest = TTSManifest(provider="fixture-tts", voice="vi",
        provider_config_fingerprint="fixture", pronunciation_fingerprint="a" * 64,
        entries=[AudioCacheEntry(scene_id="scene_001", relative_path="audio/scene_001.wav",
                                 fingerprint="sha256:" + "e" * 64,
                                 audio_sha256=hashlib.sha256(audio.read_bytes()).hexdigest(),
                                 normalized_text="Xin chào Việt Nam", duration_seconds=3)])
    atomic_write_model(directory / "audio" / "tts_manifest.json", manifest)
    return manager, project.id


def test_audio_to_words_and_ass_with_checkpoint_cache(tmp_path: Path) -> None:
    manager, project_id = project_with_audio(tmp_path)
    provider = FakeAlignmentProvider()
    coordinator = AlignmentCoordinator(manager, provider)
    words, report = coordinator.generate(project_id)
    cached, cached_report = coordinator.generate(project_id)
    directory = manager.project_dir(project_id)
    assert provider.calls == 1
    assert words.model_dump() == cached.model_dump()
    assert report == cached_report
    assert (directory / "words.json").is_file()
    assert (directory / "captions" / "subtitles.ass").is_file()
    assert json.loads((directory / "words.json").read_text(encoding="utf-8"))["language"] == "vi"
    checkpoint = CheckpointStore(directory / "checkpoint.json").load()
    assert checkpoint.stages[PipelineStage.ALIGNMENT].status is StageStatus.COMPLETED
    assert checkpoint.stages[PipelineStage.VISUALS].status is StageStatus.PENDING
