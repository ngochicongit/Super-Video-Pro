from __future__ import annotations

import json
import time
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import httpx

from newsvid_brain import (ComfyUIOutput, QueuedPrompt, VisualGenerationError,
                           VisualGenerationRequest)


class ComfyUIProvider(ABC):
    """Project-neutral boundary for an optional ComfyUI service."""

    name = "comfyui"

    @property
    @abstractmethod
    def cache_key(self) -> str: ...

    @abstractmethod
    def health_check(self) -> bool: ...

    @abstractmethod
    def queue_prompt(self, request: VisualGenerationRequest) -> QueuedPrompt: ...

    @abstractmethod
    def wait_for_completion(self, prompt_id: str) -> dict[str, Any]: ...

    @abstractmethod
    def collect_outputs(self, prompt_id: str, history: dict[str, Any]) -> list[ComfyUIOutput]: ...


class HTTPComfyUIProvider(ComfyUIProvider):
    """Adaptation of Videogen's /prompt -> /history -> /view lifecycle."""

    def __init__(self, *, base_url: str, checkpoint: str, workflow_dir: Path,
                 timeout_seconds: float = 300, poll_interval_seconds: float = 2,
                 client: httpx.Client | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.checkpoint = checkpoint
        self.workflow_dir = workflow_dir
        self.timeout_seconds = timeout_seconds
        self.poll_interval_seconds = poll_interval_seconds
        self._client = client or httpx.Client(timeout=min(timeout_seconds, 60))

    @property
    def cache_key(self) -> str:
        return f"{self.base_url}|{self.checkpoint}|phase9-v1"

    def health_check(self) -> bool:
        try:
            response = self._client.get(f"{self.base_url}/system_stats")
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    def workflow_bytes(self, request: VisualGenerationRequest) -> bytes:
        path = self.workflow_dir / f"{request.workflow.value}.json"
        try:
            template = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise VisualGenerationError(f"Invalid ComfyUI workflow {request.workflow.value}: {exc}") from exc
        replacements: dict[str, Any] = {
            "{{cfg}}": request.cfg, "{{seed}}": request.seed, "{{steps}}": request.steps,
            "{{checkpoint}}": self.checkpoint, "{{height}}": request.height,
            "{{width}}": request.width, "{{prompt}}": request.prompt,
            "{{negative_prompt}}": request.negative_prompt,
        }

        def replace(value: Any) -> Any:
            if isinstance(value, dict):
                return {key: replace(item) for key, item in value.items()}
            if isinstance(value, list):
                return [replace(item) for item in value]
            return replacements.get(value, value) if isinstance(value, str) else value

        workflow = replace(template)
        return json.dumps(workflow, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def queue_prompt(self, request: VisualGenerationRequest) -> QueuedPrompt:
        client_id = str(uuid.uuid4())
        workflow = json.loads(self.workflow_bytes(request))
        try:
            response = self._client.post(f"{self.base_url}/prompt",
                                         json={"prompt": workflow, "client_id": client_id})
            response.raise_for_status()
            prompt_id = response.json().get("prompt_id")
        except (httpx.HTTPError, ValueError) as exc:
            raise VisualGenerationError(f"ComfyUI prompt submission failed: {exc}") from exc
        if not isinstance(prompt_id, str) or not prompt_id:
            raise VisualGenerationError("ComfyUI prompt response omitted prompt_id")
        return QueuedPrompt(prompt_id=prompt_id, client_id=client_id)

    def wait_for_completion(self, prompt_id: str) -> dict[str, Any]:
        deadline = time.monotonic() + self.timeout_seconds
        while time.monotonic() <= deadline:
            try:
                response = self._client.get(f"{self.base_url}/history/{prompt_id}")
                response.raise_for_status()
                history = response.json()
            except (httpx.HTTPError, ValueError) as exc:
                raise VisualGenerationError(f"ComfyUI history request failed: {exc}") from exc
            job = history.get(prompt_id) if isinstance(history, dict) else None
            if isinstance(job, dict):
                status = job.get("status", {})
                if status.get("status_str") == "error" or status.get("completed") is False:
                    messages = status.get("messages") or []
                    raise VisualGenerationError(f"ComfyUI job {prompt_id} failed: {messages}")
                if isinstance(job.get("outputs"), dict):
                    return history
            time.sleep(self.poll_interval_seconds)
        raise VisualGenerationError(
            f"ComfyUI generation timed out after {self.timeout_seconds:g}s (prompt_id={prompt_id})"
        )

    def collect_outputs(self, prompt_id: str, history: dict[str, Any]) -> list[ComfyUIOutput]:
        job = history.get(prompt_id, {})
        outputs: list[ComfyUIOutput] = []
        for node in job.get("outputs", {}).values():
            for image in node.get("images", []):
                filename = image.get("filename")
                if not filename:
                    continue
                params = {"filename": filename, "type": image.get("type", "output")}
                if image.get("subfolder"):
                    params["subfolder"] = image["subfolder"]
                try:
                    response = self._client.get(f"{self.base_url}/view", params=params)
                    response.raise_for_status()
                except httpx.HTTPError as exc:
                    raise VisualGenerationError(f"ComfyUI output retrieval failed: {exc}") from exc
                if not response.content:
                    raise VisualGenerationError(f"ComfyUI output {filename} was empty")
                outputs.append(ComfyUIOutput(filename=filename,
                                              subfolder=image.get("subfolder", ""),
                                              type=image.get("type", "output"),
                                              content=response.content))
        if not outputs:
            raise VisualGenerationError(f"ComfyUI returned no images for prompt_id={prompt_id}")
        return outputs
