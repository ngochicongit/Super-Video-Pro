from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from newsvid.checkpoint import CheckpointStore
from newsvid.comfyui import ComfyUIProvider, HTTPComfyUIProvider
from newsvid.persistence import atomic_write_model, load_model
from newsvid.project import ProjectManager
from newsvid.schemas import PipelineStage, StageStatus
from newsvid.visuals import VisualCoordinator
from newsvid_brain import (ComfyUIOutput, ComfyUIWorkflow, NewsStyle, QueuedPrompt,
                           SceneType, SourceType, Storyboard, StoryboardScene,
                           VisualGenerationError, VisualGenerationRequest, VisualManifest,
                           VisualPlan, VisualProvenance)
from newsvid_brain.storyboard_models import StoryboardVideo

WORKFLOWS = Path(__file__).resolve().parents[2] / "workflows" / "comfyui"
PNG = b"\x89PNG\r\n\x1a\nphase-nine"


def request(workflow: ComfyUIWorkflow) -> VisualGenerationRequest:
    return VisualGenerationRequest(scene_id="scene_001", workflow=workflow,
                                   prompt="Minh họa trung tính", seed=42)


@pytest.mark.parametrize("workflow", list(ComfyUIWorkflow))
def test_all_workflows_submit_poll_and_collect_with_mock_service(workflow: ComfyUIWorkflow) -> None:
    calls: list[str] = []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append(req.url.path)
        if req.url.path == "/system_stats":
            return httpx.Response(200, request=req, json={"system": {}})
        if req.url.path == "/prompt":
            payload = json.loads(req.content)
            assert payload["prompt"]["6"]["inputs"]["text"] == "Minh họa trung tính"
            assert payload["prompt"]["3"]["inputs"]["seed"] == 42
            return httpx.Response(200, request=req, json={"prompt_id": "job-1"})
        if req.url.path == "/history/job-1":
            return httpx.Response(200, request=req, json={
                "job-1": {"status": {"completed": True}, "outputs": {
                    "9": {"images": [{"filename": "result.png", "subfolder": "", "type": "output"}]}
                }}
            })
        if req.url.path == "/view":
            return httpx.Response(200, request=req, content=PNG)
        return httpx.Response(404, request=req)

    provider = HTTPComfyUIProvider(base_url="http://127.0.0.1:8188", checkpoint="model.safetensors",
                                   workflow_dir=WORKFLOWS, poll_interval_seconds=.001,
                                   client=httpx.Client(transport=httpx.MockTransport(handler)))
    assert provider.health_check()
    queued = provider.queue_prompt(request(workflow))
    outputs = provider.collect_outputs(queued.prompt_id, provider.wait_for_completion(queued.prompt_id))
    assert outputs[0].content == PNG
    assert calls == ["/system_stats", "/prompt", "/history/job-1", "/view"]


def seed_project(tmp_path: Path, *, workflow: str = "news-image") -> tuple[ProjectManager, str, bytes]:
    manager = ProjectManager(tmp_path / "projects")
    project = manager.create("ComfyUI test")
    visual = VisualPlan(
        type=SceneType.AI_ILLUSTRATION, template="news-ai-illustration",
        provenance=VisualProvenance(source_type=SourceType.GENERATED,
                                    generator="comfyui", workflow=workflow),
        prompt="Minh họa khái niệm trí tuệ nhân tạo trung tính",
    )
    storyboard = Storyboard(
        video=StoryboardVideo(target_duration=30, style=NewsStyle.TECH_NEWS),
        scenes=[StoryboardScene(id="scene_001", script_segment_id="segment_001",
                                type=SceneType.AI_ILLUSTRATION, narration="Khái niệm mới.",
                                fact_refs=["fact_001"], duration_seconds=4, visual=visual)],
    )
    path = manager.project_dir(project.id) / "storyboard.json"
    atomic_write_model(path, storyboard)
    return manager, project.id, path.read_bytes()


class FakeProvider(ComfyUIProvider):
    cache_key = "fake|phase9"

    def __init__(self, *, fail_once: bool = False) -> None:
        self.fail_once = fail_once
        self.queues = 0

    def health_check(self) -> bool:
        return True

    def queue_prompt(self, request: VisualGenerationRequest) -> QueuedPrompt:
        self.queues += 1
        if self.fail_once:
            self.fail_once = False
            raise VisualGenerationError("service interrupted")
        return QueuedPrompt(prompt_id=f"job-{self.queues}", client_id="test-client")

    def wait_for_completion(self, prompt_id: str) -> dict[str, Any]:
        return {prompt_id: {"outputs": {"9": {"images": [{"filename": "asset.png"}]}}}}

    def collect_outputs(self, prompt_id: str, history: dict[str, Any]) -> list[ComfyUIOutput]:
        return [ComfyUIOutput(filename="asset.png", content=PNG)]


def test_generation_persists_cache_and_complete_provenance(tmp_path: Path) -> None:
    manager, project_id, _ = seed_project(tmp_path)
    provider = FakeProvider()
    coordinator = VisualCoordinator(manager, provider)
    first = coordinator.generate(project_id)
    second = coordinator.generate(project_id)
    assert provider.queues == 1 and not first.failures and not second.failures
    asset = first.assets[0]
    assert (manager.project_dir(project_id) / asset.relative_path).read_bytes() == PNG
    assert asset.provenance.model_dump() == {
        "source_type": SourceType.GENERATED, "source_url": None,
        "local_path": asset.relative_path, "generator": "comfyui", "workflow": "news-image",
    }
    storyboard = load_model(manager.project_dir(project_id) / "storyboard.json", Storyboard)
    assert storyboard.scenes[0].visual.provenance.local_path == asset.relative_path
    checkpoint = CheckpointStore(manager.project_dir(project_id) / "checkpoint.json").load()
    assert checkpoint.stages[PipelineStage.VISUALS].status is StageStatus.COMPLETED
    assert checkpoint.stages[PipelineStage.VISUALS].metadata["cache_hits"] == 1


def test_failure_is_atomic_and_resume_generates_missing_asset(tmp_path: Path) -> None:
    manager, project_id, original_storyboard = seed_project(tmp_path)
    provider = FakeProvider(fail_once=True)
    coordinator = VisualCoordinator(manager, provider)
    failed = coordinator.generate(project_id)
    directory = manager.project_dir(project_id)
    assert failed.failures and (directory / "storyboard.json").read_bytes() == original_storyboard
    checkpoint = CheckpointStore(directory / "checkpoint.json").load()
    assert checkpoint.stages[PipelineStage.VISUALS].status is StageStatus.FAILED
    resumed = coordinator.generate(project_id)
    assert not resumed.failures and resumed.assets and provider.queues == 2
    assert load_model(directory / "images" / "generated_manifest.json", VisualManifest) == resumed
    assert CheckpointStore(directory / "checkpoint.json").load().stages[PipelineStage.VISUALS].status is StageStatus.COMPLETED


def test_invalid_or_failed_comfyui_payload_is_safe() -> None:
    transport = httpx.MockTransport(lambda req: httpx.Response(200, request=req, json={}))
    provider = HTTPComfyUIProvider(base_url="http://127.0.0.1:8188", checkpoint="model.safetensors",
                                   workflow_dir=WORKFLOWS, timeout_seconds=.01,
                                   poll_interval_seconds=.001,
                                   client=httpx.Client(transport=transport))
    with pytest.raises(VisualGenerationError, match="omitted prompt_id"):
        provider.queue_prompt(request(ComfyUIWorkflow.NEWS_IMAGE))


@pytest.mark.acceptance
def test_real_comfyui_service_when_available(tmp_path: Path) -> None:
    provider = HTTPComfyUIProvider(base_url="http://127.0.0.1:8188",
                                   checkpoint="sd_xl_base_1.0.safetensors",
                                   workflow_dir=WORKFLOWS, timeout_seconds=180,
                                   poll_interval_seconds=2)
    if not provider.health_check():
        pytest.skip("optional ComfyUI service is offline")
    queued = provider.queue_prompt(request(ComfyUIWorkflow.NEWS_IMAGE))
    outputs = provider.collect_outputs(queued.prompt_id, provider.wait_for_completion(queued.prompt_id))
    path = tmp_path / "real-comfyui.png"
    path.write_bytes(outputs[0].content)
    assert path.stat().st_size > 1000
