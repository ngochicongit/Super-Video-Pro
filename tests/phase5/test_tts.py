from __future__ import annotations

import io
import hashlib
import json
import subprocess
import wave
from pathlib import Path
from typing import Any

import httpx
import pytest

from newsvid.checkpoint import CheckpointStore
from newsvid.persistence import atomic_write_model, load_model
from newsvid.project import ProjectManager
from newsvid.schemas import PipelineStage, StageStatus
from newsvid.tts import TTSCoordinator
from newsvid_brain import (F5TTSConfig, F5TTSProvider, NewsStyle, PiperConfig,
                           PiperProvider, SceneType, SourceType, Storyboard,
                           StoryboardScene, TTSError, VisualPlan, VisualProvenance,
                           load_pronunciation, normalize_vi)
from newsvid_brain.storyboard_models import StoryboardVideo
from newsvid_brain.tts_models import TTSManifest

ROOT = Path(__file__).parents[2]
PRONUNCIATION = ROOT / "config" / "pronunciation_vi.yaml"


def wav_bytes(frames: int = 160, rate: int = 16000) -> bytes:
    target = io.BytesIO()
    with wave.open(target, "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(rate)
        stream.writeframes(b"\x00\x00" * frames)
    return target.getvalue()


def test_vietnamese_normalization_uses_external_dictionary() -> None:
    config = load_pronunciation(PRONUNCIATION)
    result = normalize_vi(
        "Ngày 28/08/2026, AI dùng GPU 3 GHz, pin 5.000 mAh, tăng 15% và đạt 1.000 USD.",
        config,
    )
    assert "ngày hai mươi tám tháng tám năm hai nghìn không trăm hai mươi sáu" in result.casefold()
    assert "ây ai" in result
    assert "gi pi diu" in result
    assert "ba gi ga héc" in result
    assert "năm nghìn mi li am pe giờ" in result
    assert "mười lăm phần trăm" in result
    assert "một nghìn đô la Mỹ" in result


def test_number_year_currency_units_and_acronym_examples() -> None:
    config = load_pronunciation(PRONUNCIATION)
    result = normalize_vi("CEO báo cáo năm 2025: 21 triệu VND, CPU 2 GHz và 50 km.", config)
    assert "si i ô" in result
    assert "hai nghìn không trăm hai mươi lăm" in result
    assert "hai mươi mốt triệu đồng Việt Nam" in result
    assert "si pi diu" in result
    assert "hai gi ga héc" in result
    assert "năm mươi ki lô mét" in result


def test_piper_provider_invokes_local_cli_and_validates_wav(tmp_path: Path) -> None:
    model = tmp_path / "voice.onnx"
    model.write_bytes(b"model")
    seen: dict[str, Any] = {}

    def runner(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        seen.update(kwargs)
        output = Path(args[args.index("--output_file") + 1])
        output.write_bytes(wav_bytes())
        return subprocess.CompletedProcess(args, 0, b"", b"")

    provider = PiperProvider(PiperConfig(model_path=model, voice_name="voice-vi"), runner=runner)
    output = provider.synthesize("Xin chào", tmp_path / "out.wav", voice="voice-vi")
    assert output.is_file()
    assert seen["shell"] is False
    assert seen["input"] == "Xin chào".encode("utf-8")


def test_piper_missing_model_is_actionable(tmp_path: Path) -> None:
    provider = PiperProvider(PiperConfig(model_path=tmp_path / "missing.onnx"))
    with pytest.raises(TTSError, match="model not found"):
        provider.synthesize("Xin chào", tmp_path / "out.wav", voice="vi_VN-vais1000-medium")


def test_optional_f5_service_retries_transient_error_and_returns_wav(tmp_path: Path) -> None:
    calls: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(json.loads(request.content))
        if len(calls) == 1:
            return httpx.Response(503, request=request)
        return httpx.Response(200, request=request, content=wav_bytes(),
                              headers={"content-type": "audio/wav"})

    provider = F5TTSProvider(F5TTSConfig(max_attempts=2),
                             transport=httpx.MockTransport(handler), sleeper=lambda _: None)
    output = provider.synthesize("Xin chào Việt Nam", tmp_path / "f5.wav", voice="female-vi")
    assert output.is_file()
    assert len(calls) == 2
    assert calls[0] == {"text": "Xin chào Việt Nam", "voice": "female-vi",
                        "language": "vi", "speed": 1.0, "format": "wav"}


def test_f5_service_rejects_non_loopback_endpoint() -> None:
    with pytest.raises(ValueError, match="loopback"):
        F5TTSProvider(F5TTSConfig(base_url="https://tts.example.com"))


def graphic() -> VisualPlan:
    return VisualPlan(type=SceneType.KINETIC_TEXT, template="frame-kinetic-type",
                      provenance=VisualProvenance(source_type=SourceType.GRAPHIC))


def storyboard() -> Storyboard:
    narrations = [
        "AI vừa công bố bản tin mới.",
        "Kế hoạch tăng 15% trong năm 2026.",
        "Đây là những thông tin chính.",
    ]
    types = [SceneType.HOOK, SceneType.KINETIC_TEXT, SceneType.OUTRO]
    return Storyboard(video=StoryboardVideo(target_duration=60, style=NewsStyle.TECH_NEWS),
                      scenes=[StoryboardScene(
                          id=f"scene_{index:03d}", script_segment_id=f"segment_{index:03d}",
                          type=types[index - 1], narration=text, fact_refs=["fact_001"],
                          duration_seconds=20, visual=graphic(),
                      ) for index, text in enumerate(narrations, 1)])


class FakeTTSProvider:
    name = "fake-tts"

    def __init__(self, key: str = "fake-config-v1") -> None:
        self.cache_key = key
        self.calls: list[tuple[str, str, Path]] = []

    def synthesize(self, text: str, output_path: Path, *, voice: str) -> Path:
        self.calls.append((text, voice, output_path))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(wav_bytes())
        return output_path


def project_with_storyboard(tmp_path: Path) -> tuple[ProjectManager, str]:
    manager = ProjectManager(tmp_path / "projects")
    project = manager.create("TTS test")
    directory = manager.project_dir(project.id)
    atomic_write_model(directory / "storyboard.json", storyboard())
    CheckpointStore(directory / "checkpoint.json").update(
        PipelineStage.STORYBOARD, StageStatus.COMPLETED, fingerprint="sha256:storyboard"
    )
    return manager, project.id


def test_scene_wavs_manifest_and_deterministic_cache(tmp_path: Path) -> None:
    manager, project_id = project_with_storyboard(tmp_path)
    provider = FakeTTSProvider()
    coordinator = TTSCoordinator(manager, provider, load_pronunciation(PRONUNCIATION), voice="voice-vi")
    first = coordinator.generate(project_id)
    second = coordinator.generate(project_id)
    directory = manager.project_dir(project_id)
    assert len(provider.calls) == 3
    assert [entry.relative_path for entry in first.entries] == [
        "audio/scene_001.wav", "audio/scene_002.wav", "audio/scene_003.wav"]
    assert all((directory / entry.relative_path).is_file() for entry in first.entries)
    assert second.model_dump() == first.model_dump()
    assert "ây ai" in first.entries[0].normalized_text
    assert "mười lăm phần trăm" in first.entries[1].normalized_text
    checkpoint = CheckpointStore(directory / "checkpoint.json").load()
    assert checkpoint.stages[PipelineStage.TTS].status is StageStatus.COMPLETED
    assert checkpoint.stages[PipelineStage.TTS].metadata["cache_hits"] == 3
    assert not (directory / "captions" / "scene_001.words.json").exists()


def test_only_changed_narration_regenerates_and_provider_config_invalidates_all(tmp_path: Path) -> None:
    manager, project_id = project_with_storyboard(tmp_path)
    config = load_pronunciation(PRONUNCIATION)
    provider = FakeTTSProvider()
    TTSCoordinator(manager, provider, config, voice="voice-vi").generate(project_id)
    directory = manager.project_dir(project_id)
    outputs = {scene_id: directory / "audio" / f"{scene_id}.wav"
               for scene_id in ("scene_001", "scene_002", "scene_003")}
    before = {scene_id: (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns)
              for scene_id, path in outputs.items()}
    board = load_model(directory / "storyboard.json", Storyboard)
    board.scenes[1].narration = "Kế hoạch tăng 20% trong năm 2026."
    atomic_write_model(directory / "storyboard.json", board)
    TTSCoordinator(manager, provider, config, voice="voice-vi").generate(project_id)
    assert len(provider.calls) == 4
    after = {scene_id: (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns)
             for scene_id, path in outputs.items()}
    assert after["scene_001"] == before["scene_001"]
    assert after["scene_003"] == before["scene_003"]
    assert after["scene_002"] != before["scene_002"]
    TTSCoordinator(manager, provider, config, voice="voice-vi").generate(project_id)
    cached = {scene_id: (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns)
              for scene_id, path in outputs.items()}
    assert cached == after and len(provider.calls) == 4
    changed_provider = FakeTTSProvider("fake-config-v2")
    TTSCoordinator(manager, changed_provider, config, voice="voice-vi").generate(project_id)
    assert len(changed_provider.calls) == 3


def test_corrupt_cached_wav_regenerates_scene(tmp_path: Path) -> None:
    manager, project_id = project_with_storyboard(tmp_path)
    provider = FakeTTSProvider()
    coordinator = TTSCoordinator(manager, provider, load_pronunciation(PRONUNCIATION), voice="voice-vi")
    coordinator.generate(project_id)
    output = manager.project_dir(project_id) / "audio" / "scene_002.wav"
    output.write_bytes(b"not wav")
    manifest = coordinator.generate(project_id)
    assert len(provider.calls) == 4
    assert isinstance(manifest, TTSManifest)
