from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from newsvid.checkpoint import CheckpointStore
from newsvid.facts import FactsCoordinator
from newsvid.ingestion import IngestionCoordinator
from newsvid.project import ProjectManager
from newsvid.schemas import PipelineStage, StageStatus
from newsvid_brain import GroundingError, LLMError, OllamaConfig, OllamaProvider, StructuredOutputError

ROOT = Path(__file__).parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "article_vi.html"
FIXTURE_URL = "https://news.example.vn/cong-nghe/trung-tam-ai"


class FakeProvider:
    cache_key = "fake:grounded:v1"

    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.calls = 0

    def generate_structured(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        self.calls += 1
        assert "SOURCE ARTICLE" in prompt
        assert schema["type"] == "object"
        return self.payload


def valid_payload() -> dict[str, Any]:
    return {"facts": [
        {"claim": "Trung tâm được công bố tại Thành phố Hồ Chí Minh.",
         "evidence": "được công bố tại Thành phố Hồ Chí Minh",
         "importance": 0.9, "confidence": 0.98},
        {"claim": "Trung tâm sẽ đào tạo một nghìn kỹ sư trong ba năm.",
         "evidence": "đào tạo một nghìn kỹ sư trong ba năm",
         "importance": 0.8, "confidence": 0.95},
    ]}


def project_with_article(tmp_path: Path) -> tuple[ProjectManager, str]:
    manager = ProjectManager(tmp_path / "projects")
    project = IngestionCoordinator(manager).ingest_file(FIXTURE, source_url=FIXTURE_URL)
    return manager, project.id


def test_article_to_grounded_facts_and_checkpoint(tmp_path: Path) -> None:
    manager, project_id = project_with_article(tmp_path)
    result = FactsCoordinator(manager, FakeProvider(valid_payload())).extract(project_id)
    directory = manager.project_dir(project_id)
    saved = json.loads((directory / "facts.json").read_text(encoding="utf-8"))
    checkpoint = CheckpointStore(directory / "checkpoint.json").load()
    assert [fact.id for fact in result.facts] == ["fact_001", "fact_002"]
    assert len({fact["id"] for fact in saved["facts"]}) == 2
    assert saved["source"]["url"] == FIXTURE_URL
    assert saved["source"]["publisher"] == "news.example.vn"
    assert all(fact["evidence"] for fact in saved["facts"])
    assert checkpoint.stages[PipelineStage.FACTS].status is StageStatus.COMPLETED
    assert not (directory / "script.json").exists()


def test_matching_fingerprint_uses_valid_cached_facts(tmp_path: Path) -> None:
    manager, project_id = project_with_article(tmp_path)
    provider = FakeProvider(valid_payload())
    coordinator = FactsCoordinator(manager, provider)
    coordinator.extract(project_id)
    coordinator.extract(project_id)
    assert provider.calls == 1


@pytest.mark.parametrize("payload", [
    {"facts": [{"claim": "x", "importance": 0.5, "confidence": 0.5}]},
    {"facts": [{"claim": "x", "evidence": "x", "importance": 2, "confidence": 0.5}]},
    {"facts": []},
    {"facts": [], "unexpected": True},
])
def test_invalid_schema_fails_without_writing_output(tmp_path: Path, payload: dict[str, Any]) -> None:
    manager, project_id = project_with_article(tmp_path)
    with pytest.raises(StructuredOutputError):
        FactsCoordinator(manager, FakeProvider(payload)).extract(project_id)
    directory = manager.project_dir(project_id)
    assert not (directory / "facts.json").exists()
    checkpoint = CheckpointStore(directory / "checkpoint.json").load()
    assert checkpoint.stages[PipelineStage.FACTS].status is StageStatus.FAILED


def test_non_verbatim_evidence_is_rejected(tmp_path: Path) -> None:
    manager, project_id = project_with_article(tmp_path)
    payload = valid_payload()
    payload["facts"][0]["evidence"] = "Nội dung hoàn toàn không có trong bài"
    with pytest.raises(GroundingError):
        FactsCoordinator(manager, FakeProvider(payload)).extract(project_id)


def test_article_wrapper_is_removed_before_grounding_and_persistence(tmp_path: Path) -> None:
    manager, project_id = project_with_article(tmp_path)
    payload = valid_payload()
    original = payload["facts"][0]["evidence"]
    payload["facts"][0]["evidence"] = f"<article>\n{original}\n</article>"

    result = FactsCoordinator(manager, FakeProvider(payload)).extract(project_id)

    assert result.facts[0].evidence == original
    saved = json.loads((manager.project_dir(project_id) / "facts.json").read_text(encoding="utf-8"))
    assert saved["facts"][0]["evidence"] == original


def test_article_wrapper_does_not_make_ungrounded_evidence_valid(tmp_path: Path) -> None:
    manager, project_id = project_with_article(tmp_path)
    payload = valid_payload()
    payload["facts"][0]["evidence"] = "<article>Nội dung không có trong bài</article>"

    with pytest.raises(GroundingError):
        FactsCoordinator(manager, FakeProvider(payload)).extract(project_id)


def test_invalid_ollama_json_is_safe() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(
        200, request=request, json={"message": {"content": "```json not-valid ```"}}
    ))
    provider = OllamaProvider(OllamaConfig(max_attempts=3), transport=transport, sleeper=lambda _: None)
    with pytest.raises(StructuredOutputError):
        provider.generate_structured("prompt", {"type": "object"})


def test_ollama_retries_only_transient_statuses_and_sends_schema() -> None:
    calls: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(json.loads(request.content))
        if len(calls) == 1:
            return httpx.Response(503, request=request)
        return httpx.Response(200, request=request,
                              json={"message": {"content": '{"facts": []}'}})

    provider = OllamaProvider(OllamaConfig(max_attempts=2),
                              transport=httpx.MockTransport(handler), sleeper=lambda _: None)
    result = provider.generate_structured("prompt", {"type": "object"})
    assert result == {"facts": []}
    assert len(calls) == 2
    assert calls[0]["format"] == {"type": "object"}
    assert calls[0]["stream"] is False


def test_ollama_connection_error_is_actionable() -> None:
    def unavailable(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    provider = OllamaProvider(
        OllamaConfig(base_url="http://127.0.0.1:11434", model="qwen2.5:7b", max_attempts=1),
        transport=httpx.MockTransport(unavailable), sleeper=lambda _: None,
    )
    with pytest.raises(LLMError) as captured:
        provider.generate_structured("prompt", {"type": "object"})
    message = str(captured.value)
    assert "cannot connect to http://127.0.0.1:11434" in message
    assert "ollama pull qwen2.5:7b" in message
