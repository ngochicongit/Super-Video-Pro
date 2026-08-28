from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from newsvid.checkpoint import CheckpointStore
from newsvid.persistence import atomic_write_model
from newsvid.project import ProjectManager
from newsvid.schemas import PipelineStage, StageStatus
from newsvid.scripts import ScriptCoordinator
from newsvid_brain import Fact, FactSet, FactSource, NewsStyle, SchemaValidationError


class FakeProvider:
    cache_key = "fake:script:v1"

    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.calls = 0

    def generate_structured(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        self.calls += 1
        assert "hoàn toàn bằng tiếng Việt" in prompt
        assert "fact_001" in prompt
        assert schema["type"] == "object"
        return self.payload


def narration(words: int, *, vietnamese: bool = True) -> str:
    source = ("Trung tâm được công bố tại thành phố và sẽ đào tạo kỹ sư trong ba năm theo kế hoạch "
              if vietnamese else "The center announced a program that trains engineers over the next three years ")
    tokens = source.split()
    return " ".join(tokens[index % len(tokens)] for index in range(words)) + "."


def valid_payload(target_words: int = 150) -> dict[str, Any]:
    first = target_words // 3
    return {"title": "Trung tâm AI mới tại Việt Nam", "segments": [
        {"type": "hook", "narration": narration(first), "fact_refs": ["fact_001"]},
        {"type": "body", "narration": narration(first), "fact_refs": ["fact_001", "fact_002"]},
        {"type": "outro", "narration": narration(target_words - first * 2), "fact_refs": ["fact_002"]},
    ]}


def project_with_facts(tmp_path: Path) -> tuple[ProjectManager, str]:
    manager = ProjectManager(tmp_path / "projects")
    project = manager.create("Bản tin AI")
    facts = FactSet(
        source=FactSource(url="https://news.example.vn/ai", publisher="news.example.vn",
                          title="Việt Nam ra mắt trung tâm AI mới"),
        facts=[
            Fact(id="fact_001", claim="Trung tâm AI mới được công bố.",
                 evidence="Trung tâm AI mới được công bố.", importance=0.9, confidence=0.98),
            Fact(id="fact_002", claim="Trung tâm sẽ đào tạo kỹ sư trong ba năm.",
                 evidence="Trung tâm sẽ đào tạo kỹ sư trong ba năm.", importance=0.8, confidence=0.95),
        ],
    )
    directory = manager.project_dir(project.id)
    atomic_write_model(directory / "facts.json", facts)
    CheckpointStore(directory / "checkpoint.json").update(
        PipelineStage.FACTS, StageStatus.COMPLETED, fingerprint="sha256:test"
    )
    return manager, project.id


def test_facts_to_default_vietnamese_script(tmp_path: Path) -> None:
    manager, project_id = project_with_facts(tmp_path)
    script = ScriptCoordinator(manager, FakeProvider(valid_payload())).generate(project_id)
    saved = json.loads((manager.project_dir(project_id) / "script.json").read_text(encoding="utf-8"))
    checkpoint = CheckpointStore(manager.project_dir(project_id) / "checkpoint.json").load()
    assert script.language == "vi"
    assert script.target_duration_seconds == 60
    assert 48 <= script.estimated_duration_seconds <= 72
    assert [segment.id for segment in script.segments] == ["segment_001", "segment_002", "segment_003"]
    assert all(segment.fact_refs for segment in script.segments)
    assert saved["style"] == "breaking-news"
    assert checkpoint.stages[PipelineStage.SCRIPT].status is StageStatus.COMPLETED
    assert not (manager.project_dir(project_id) / "storyboard.json").exists()


@pytest.mark.parametrize("style", list(NewsStyle))
def test_all_supported_styles(tmp_path: Path, style: NewsStyle) -> None:
    manager, project_id = project_with_facts(tmp_path)
    script = ScriptCoordinator(manager, FakeProvider(valid_payload())).generate(
        project_id, style=style
    )
    assert script.style is style


@pytest.mark.parametrize("duration", [30, 45, 60, 90])
def test_supported_duration_targets(tmp_path: Path, duration: int) -> None:
    manager, project_id = project_with_facts(tmp_path)
    words = round(duration * 2.5)
    script = ScriptCoordinator(manager, FakeProvider(valid_payload(words))).generate(
        project_id, target_duration=duration
    )
    assert abs(script.estimated_duration_seconds - duration) <= duration * 0.2


def test_unresolved_fact_reference_is_rejected_and_checkpoint_fails(tmp_path: Path) -> None:
    manager, project_id = project_with_facts(tmp_path)
    payload = valid_payload()
    payload["segments"][1]["fact_refs"] = ["fact_999"]
    with pytest.raises(SchemaValidationError, match="unresolved"):
        ScriptCoordinator(manager, FakeProvider(payload)).generate(project_id)
    assert not (manager.project_dir(project_id) / "script.json").exists()
    checkpoint = CheckpointStore(manager.project_dir(project_id) / "checkpoint.json").load()
    assert checkpoint.stages[PipelineStage.SCRIPT].status is StageStatus.FAILED


def test_factual_segment_without_refs_is_rejected(tmp_path: Path) -> None:
    manager, project_id = project_with_facts(tmp_path)
    payload = valid_payload()
    payload["segments"][0]["fact_refs"] = []
    with pytest.raises(SchemaValidationError, match="must contain fact_refs"):
        ScriptCoordinator(manager, FakeProvider(payload)).generate(project_id)


def test_non_vietnamese_and_wrong_duration_are_rejected(tmp_path: Path) -> None:
    manager, project_id = project_with_facts(tmp_path)
    english = valid_payload()
    for segment in english["segments"]:
        segment["narration"] = narration(50, vietnamese=False)
    with pytest.raises(SchemaValidationError, match="Vietnamese"):
        ScriptCoordinator(manager, FakeProvider(english)).generate(project_id)
    with pytest.raises(SchemaValidationError, match="target window"):
        ScriptCoordinator(manager, FakeProvider(valid_payload(30))).generate(
            project_id, style=NewsStyle.DOCUMENTARY
        )


def test_cache_hit_skips_provider(tmp_path: Path) -> None:
    manager, project_id = project_with_facts(tmp_path)
    provider = FakeProvider(valid_payload())
    coordinator = ScriptCoordinator(manager, provider)
    coordinator.generate(project_id)
    coordinator.generate(project_id)
    assert provider.calls == 1
