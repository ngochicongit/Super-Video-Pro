from __future__ import annotations

import hashlib

from newsvid_brain import FactSet, NewsScript
from newsvid_brain.storyboard_models import Storyboard
from newsvid_brain.storyboard_service import StoryboardBuilder
from newsvid_brain.visual_router import RoutingContext, VISUAL_ROUTER_VERSION
from newsvid_ingest.models import ImageManifest

from .checkpoint import CheckpointStore
from .persistence import atomic_write_model, load_model
from .project import ProjectManager
from .schemas import PipelineStage, StageStatus


class StoryboardCoordinator:
    def __init__(self, projects: ProjectManager, builder: StoryboardBuilder | None = None) -> None:
        self.projects = projects
        self.builder = builder or StoryboardBuilder()

    def build(self, project_id: str) -> Storyboard:
        directory = self.projects.project_dir(project_id)
        self.projects.load(project_id)
        facts = load_model(directory / "facts.json", FactSet)
        script = load_model(directory / "script.json", NewsScript)
        images = load_model(directory / "images.json", ImageManifest)
        image = next((item for item in images.images if item.is_hero), None)
        image = image or (images.images[0] if images.images else None)
        context = RoutingContext(
            article_image_url=str(image.source_url) if image else None,
            article_url=str(facts.source.url),
        )
        digest = hashlib.sha256()
        for value in (facts.model_dump_json(), script.model_dump_json(), images.model_dump_json(),
                      VISUAL_ROUTER_VERSION):
            digest.update(value.encode("utf-8"))
        fingerprint = f"sha256:{digest.hexdigest()}"
        store = CheckpointStore(directory / "checkpoint.json")
        checkpoint = store.load().stages[PipelineStage.STORYBOARD]
        output = directory / "storyboard.json"
        if checkpoint.status is StageStatus.COMPLETED and checkpoint.fingerprint == fingerprint:
            try:
                return load_model(output, Storyboard)
            except (OSError, ValueError):
                pass
        store.update(PipelineStage.STORYBOARD, StageStatus.RUNNING, fingerprint=fingerprint)
        try:
            storyboard = self.builder.build(script, facts, context)
            atomic_write_model(output, storyboard)
            counts: dict[str, int] = {}
            for scene in storyboard.scenes:
                key = scene.visual.type.value
                counts[key] = counts.get(key, 0) + 1
            store.update(PipelineStage.STORYBOARD, StageStatus.COMPLETED, fingerprint=fingerprint,
                         metadata={"scene_count": len(storyboard.scenes),
                                   "visual_counts": counts,
                                   "router_version": VISUAL_ROUTER_VERSION})
            return storyboard
        except Exception as exc:
            store.update(PipelineStage.STORYBOARD, StageStatus.FAILED, fingerprint=fingerprint,
                         error=f"{type(exc).__name__}: {exc}")
            raise
