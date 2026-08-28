from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path

from newsvid_brain import (ComfyUIWorkflow, GeneratedVisualAsset, SourceType, Storyboard,
                           VisualFailure, VisualGenerationError, VisualGenerationRequest,
                           VisualManifest, VisualProvenance)

from .checkpoint import CheckpointStore
from .comfyui import ComfyUIProvider, HTTPComfyUIProvider
from .persistence import atomic_write_model, load_model
from .project import ProjectManager
from .schemas import PipelineStage, StageStatus


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _atomic_write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def _validate_image(payload: bytes) -> None:
    valid = (payload.startswith(b"\x89PNG\r\n\x1a\n")
             or payload.startswith(b"\xff\xd8\xff")
             or (payload.startswith(b"RIFF") and payload[8:12] == b"WEBP"))
    if not valid:
        raise VisualGenerationError("ComfyUI returned an unsupported or invalid image")


class VisualCoordinator:
    def __init__(self, projects: ProjectManager, provider: ComfyUIProvider) -> None:
        self.projects = projects
        self.provider = provider

    def generate(self, project_id: str) -> VisualManifest:
        directory = self.projects.project_dir(project_id)
        self.projects.load(project_id)
        storyboard_path = directory / "storyboard.json"
        storyboard = load_model(storyboard_path, Storyboard)
        targets = [scene for scene in storyboard.scenes
                   if scene.visual.provenance.source_type is SourceType.GENERATED
                   and scene.visual.provenance.generator == "comfyui"]
        manifest_path = directory / "images" / "generated_manifest.json"
        try:
            previous = load_model(manifest_path, VisualManifest)
        except (OSError, ValueError):
            previous = VisualManifest()
        target_ids = {scene.id for scene in targets}
        assets = {asset.scene_id: asset for asset in previous.assets if asset.scene_id in target_ids}
        failures: list[VisualFailure] = []
        requests = {scene.id: self._request(scene) for scene in targets}
        fingerprints = {scene_id: self._fingerprint(request) for scene_id, request in requests.items()}
        stage_digest = hashlib.sha256()
        stage_digest.update(storyboard.model_dump_json().encode("utf-8"))
        stage_digest.update(self.provider.cache_key.encode("utf-8"))
        for scene_id in sorted(fingerprints):
            stage_digest.update(fingerprints[scene_id].encode("ascii"))
        stage_fingerprint = f"sha256:{stage_digest.hexdigest()}"
        store = CheckpointStore(directory / "checkpoint.json")
        store.update(PipelineStage.VISUALS, StageStatus.RUNNING, fingerprint=stage_fingerprint)
        cache_hits = 0
        generated = 0

        for scene in targets:
            request = requests[scene.id]
            fingerprint = fingerprints[scene.id]
            existing = assets.get(scene.id)
            if existing and existing.fingerprint == fingerprint:
                path = directory / existing.relative_path
                if path.is_file() and _sha256(path.read_bytes()) == existing.content_sha256:
                    cache_hits += 1
                    continue
            try:
                if not self.provider.health_check():
                    raise VisualGenerationError("ComfyUI is optional and currently offline")
                queued = self.provider.queue_prompt(request)
                history = self.provider.wait_for_completion(queued.prompt_id)
                output = self.provider.collect_outputs(queued.prompt_id, history)[0]
                _validate_image(output.content)
                suffix = Path(output.filename).suffix.lower()
                if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
                    suffix = ".png"
                relative_path = f"images/generated/{scene.id}-{fingerprint[7:19]}{suffix}"
                output_path = directory / relative_path
                _atomic_write_bytes(output_path, output.content)
                content_sha = _sha256(output.content)
                assets[scene.id] = GeneratedVisualAsset(
                    scene_id=scene.id, workflow=request.workflow, relative_path=relative_path,
                    fingerprint=fingerprint, content_sha256=content_sha,
                    prompt_id=queued.prompt_id,
                    provenance=VisualProvenance(source_type=SourceType.GENERATED,
                                                local_path=relative_path, generator="comfyui",
                                                workflow=request.workflow.value),
                )
                generated += 1
                atomic_write_model(manifest_path, VisualManifest(assets=list(assets.values())))
            except Exception as exc:
                failures.append(VisualFailure(scene_id=scene.id, workflow=request.workflow,
                                              error=f"{type(exc).__name__}: {exc}"))

        manifest = VisualManifest(assets=[assets[key] for key in sorted(assets)], failures=failures)
        atomic_write_model(manifest_path, manifest)
        if failures:
            store.update(PipelineStage.VISUALS, StageStatus.FAILED, fingerprint=stage_fingerprint,
                         error=f"{len(failures)} optional ComfyUI visual(s) failed",
                         metadata={"generated": generated, "cache_hits": cache_hits,
                                   "failed_scenes": [item.scene_id for item in failures]})
            return manifest

        updated = storyboard.model_copy(deep=True)
        by_scene = {asset.scene_id: asset for asset in manifest.assets}
        for scene in updated.scenes:
            if scene.id in by_scene:
                scene.visual.provenance = by_scene[scene.id].provenance
        atomic_write_model(storyboard_path, updated)
        store.update(PipelineStage.VISUALS, StageStatus.COMPLETED, fingerprint=stage_fingerprint,
                     metadata={"generated": generated, "cache_hits": cache_hits,
                               "asset_count": len(manifest.assets)})
        return manifest

    def _request(self, scene: object) -> VisualGenerationRequest:
        visual = scene.visual  # type: ignore[attr-defined]
        workflow = ComfyUIWorkflow(visual.provenance.workflow or "news-image")
        style = {
            ComfyUIWorkflow.NEWS_IMAGE: "editorial news photograph, realistic, vertical composition",
            ComfyUIWorkflow.BACKGROUND: "clean cinematic news background, no people, room for captions",
            ComfyUIWorkflow.INFOGRAPHIC: "clear editorial infographic, simple shapes, no embedded text",
        }[workflow]
        prompt = f"{visual.prompt}. {style}".strip(". ")
        seed_source = f"{scene.id}|{workflow.value}|{prompt}"  # type: ignore[attr-defined]
        seed = int(hashlib.sha256(seed_source.encode("utf-8")).hexdigest()[:16], 16) % (2**63)
        return VisualGenerationRequest(scene_id=scene.id, workflow=workflow, prompt=prompt, seed=seed)  # type: ignore[attr-defined]

    def _fingerprint(self, request: VisualGenerationRequest) -> str:
        digest = hashlib.sha256()
        digest.update(request.model_dump_json().encode("utf-8"))
        digest.update(self.provider.cache_key.encode("utf-8"))
        if isinstance(self.provider, HTTPComfyUIProvider):
            digest.update(self.provider.workflow_bytes(request))
        return f"sha256:{digest.hexdigest()}"
