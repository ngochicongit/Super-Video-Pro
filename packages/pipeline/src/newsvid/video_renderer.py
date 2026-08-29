from __future__ import annotations

import hashlib
from pathlib import Path

from newsvid_brain import (FactSet, ImageAsset, PreviewResult, RenderError, RenderManifest,
                           RenderedScene, SceneManifest, SourceType, Storyboard, TransitionConfig,
                           TransitionType, VisualManifest)
from newsvid_brain.tts_models import TTSManifest
from newsvid_ingest.models import ImageManifest

from .article_renderer import ArticleImageCache, EFFECTS
from .checkpoint import CheckpointStore
from .final_assembler import FinalAssembler
from .motion_renderer import MOTION_TYPES, SceneRenderer
from .persistence import atomic_write_model, load_model
from .project import ProjectManager
from .schemas import PipelineStage, StageStatus
from .selective_regeneration import ChangeKind, InvalidationPlan, plan_invalidation


TARGET_WIDTH = 1080
TARGET_HEIGHT = 1920
TARGET_FPS = 30
SCENE_RENDER_VERSION = "unified-scene-render-v1"


class VideoRenderCoordinator:
    """One project pipeline: SceneRenderer -> RenderedScene -> FinalAssembler."""

    def __init__(self, projects: ProjectManager, image_cache: ArticleImageCache,
                 scene_renderer: SceneRenderer, assembler: FinalAssembler) -> None:
        self.projects = projects
        self.image_cache = image_cache
        self.scene_renderer = scene_renderer
        self.assembler = assembler

    @staticmethod
    def dependency_plan(kind: ChangeKind | str, scene_ids: list[str] | tuple[str, ...] = ()) -> InvalidationPlan:
        return plan_invalidation(kind, scene_ids)

    def preview(self, project_id: str, *, transition: TransitionConfig) -> PreviewResult:
        directory, storyboard, rendered, _, preview_fingerprint = self._render_scenes(
            project_id, transition=transition
        )
        subtitles = directory / "captions" / "subtitles.ass"
        if not subtitles.is_file():
            raise RenderError("Phase 6 ASS subtitles are required")
        preview_digest = hashlib.sha256()
        preview_digest.update(preview_fingerprint.encode("ascii"))
        preview_digest.update(_sha256_file(subtitles).encode("ascii"))
        preview_fingerprint = f"sha256:{preview_digest.hexdigest()}"
        preview_path = directory / "output" / "preview.mp4"
        store = CheckpointStore(directory / "checkpoint.json")
        checkpoint = store.load().stages[PipelineStage.PREVIEW]
        if not (checkpoint.status is StageStatus.COMPLETED
                and checkpoint.fingerprint == preview_fingerprint and preview_path.is_file()):
            store.update(PipelineStage.PREVIEW, StageStatus.RUNNING,
                         fingerprint=preview_fingerprint)
            try:
                self.assembler.assemble_preview(
                    rendered, directory, preview_path, transition=transition,
                    width=TARGET_WIDTH, height=TARGET_HEIGHT, fps=TARGET_FPS,
                    subtitles=subtitles,
                )
                probe = self.assembler.probe(preview_path)
                self._validate_target(probe, "Preview")
                store.update(PipelineStage.PREVIEW, StageStatus.COMPLETED,
                             fingerprint=preview_fingerprint,
                             metadata={"output": "output/preview.mp4",
                                       "duration_seconds": probe.duration_seconds,
                                       "transition": transition.model_dump(mode="json")})
            except Exception as exc:
                preview_path.unlink(missing_ok=True)
                store.update(PipelineStage.PREVIEW, StageStatus.FAILED,
                             fingerprint=preview_fingerprint,
                             error=f"{type(exc).__name__}: {exc}")
                raise
        probe = self.assembler.probe(preview_path)
        self._validate_target(probe, "Preview")
        return PreviewResult(fingerprint=preview_fingerprint, transition=transition,
                             scenes=rendered, probe=probe)

    def render(self, project_id: str, *, transition: TransitionConfig) -> RenderManifest:
        preview = self.preview(project_id, transition=transition)
        directory = self.projects.project_dir(project_id)
        final_digest = hashlib.sha256()
        for value in (preview.fingerprint, self.assembler.cache_key):
            final_digest.update(value.encode("utf-8"))
        final_fingerprint = f"sha256:{final_digest.hexdigest()}"
        final_path = directory / "output" / "final.mp4"
        manifest_path = directory / "output" / "render_manifest.json"
        store = CheckpointStore(directory / "checkpoint.json")
        checkpoint = store.load().stages[PipelineStage.FINAL_RENDER]
        if checkpoint.status is StageStatus.COMPLETED and checkpoint.fingerprint == final_fingerprint:
            try:
                cached = load_model(manifest_path, RenderManifest)
                if final_path.is_file() and cached.fingerprint == final_fingerprint:
                    self._validate_target(cached.probe, "Final")
                    return cached
            except (OSError, ValueError, RenderError):
                pass
        store.update(PipelineStage.FINAL_RENDER, StageStatus.RUNNING,
                     fingerprint=final_fingerprint)
        try:
            self.assembler.finalize(directory / preview.output_path, final_path)
            probe = self.assembler.probe(final_path)
            self._validate_target(probe, "Final")
            article_assets = self._article_assets(directory, preview.scenes)
            comfyui_used = any(scene.renderer == "ffmpeg-ai-image" for scene in preview.scenes)
            manifest = RenderManifest(
                fingerprint=final_fingerprint, width=TARGET_WIDTH, height=TARGET_HEIGHT,
                fps=TARGET_FPS, scenes=preview.scenes, assets=article_assets, probe=probe,
                transition=transition, comfyui_used=comfyui_used,
            )
            atomic_write_model(manifest_path, manifest)
            store.update(PipelineStage.FINAL_RENDER, StageStatus.COMPLETED,
                         fingerprint=final_fingerprint,
                         metadata={"output": manifest.output_path,
                                   "duration_seconds": probe.duration_seconds,
                                   "resolution": f"{probe.width}x{probe.height}",
                                   "fps": probe.fps, "video_codec": probe.video_codec,
                                   "audio_codec": probe.audio_codec})
            return manifest
        except Exception as exc:
            final_path.unlink(missing_ok=True)
            store.update(PipelineStage.FINAL_RENDER, StageStatus.FAILED,
                         fingerprint=final_fingerprint,
                         error=f"{type(exc).__name__}: {exc}")
            raise

    def render_scene(self, project_id: str, scene_id: str) -> RenderedScene:
        directory, _, rendered, _, _ = self._render_scenes(project_id, transition=TransitionConfig())
        for scene in rendered:
            if scene.scene_id == scene_id:
                path = directory / scene.video_path
                if not path.is_file() or path.stat().st_size == 0:
                    raise RenderError(f"Scene output is missing or empty: {scene_id}")
                return scene
        raise RenderError(f"Unknown storyboard scene: {scene_id}")

    def _render_scenes(self, project_id: str, *, transition: TransitionConfig
                       ) -> tuple[Path, Storyboard, list[RenderedScene], list[ImageAsset], str]:
        directory = self.projects.project_dir(project_id)
        self.projects.load(project_id)
        storyboard = load_model(directory / "storyboard.json", Storyboard)
        facts = load_model(directory / "facts.json", FactSet)
        fact_ids = {fact.id for fact in facts.facts}
        unresolved = sorted({ref for scene in storyboard.scenes for ref in scene.fact_refs
                             if ref not in fact_ids})
        if unresolved:
            raise RenderError(f"Storyboard contains unresolved fact references: {', '.join(unresolved)}")
        if (storyboard.video.width, storyboard.video.height, storyboard.video.fps) != (
                TARGET_WIDTH, TARGET_HEIGHT, TARGET_FPS):
            raise RenderError("Phase 10 requires storyboard video settings 1080x1920 at 30fps")
        images = load_model(directory / "images.json", ImageManifest)
        tts = load_model(directory / "audio" / "tts_manifest.json", TTSManifest)
        entries = {entry.scene_id: entry for entry in tts.entries}
        if set(entries) != {scene.id for scene in storyboard.scenes}:
            raise RenderError("TTS manifest does not cover every storyboard scene")
        try:
            generated = load_model(directory / "images" / "generated_manifest.json", VisualManifest)
        except (OSError, ValueError):
            generated = VisualManifest()
        generated_by_scene = {asset.scene_id: asset for asset in generated.assets}
        acquired: dict[str, tuple[Path, ImageAsset]] = {}
        article_assets: list[ImageAsset] = []
        store = CheckpointStore(directory / "checkpoint.json")
        prior_scenes: dict[str, RenderedScene] = {}
        manifest_path = directory / "scenes" / "manifest.json"
        try:
            prior_scenes = {item.scene_id: item for item in
                            load_model(manifest_path, SceneManifest).scenes}
        except (OSError, ValueError):
            pass
        store.update(PipelineStage.SCENES, StageStatus.RUNNING)
        rendered: list[RenderedScene] = []
        try:
            for index, scene in enumerate(storyboard.scenes):
                image, source_path, source_hash, asset = self._resolve_visual(
                    scene, index, directory, images, generated_by_scene, acquired
                )
                if asset and all(existing.sha256 != asset.sha256 for existing in article_assets):
                    article_assets.append(asset)
                audio_entry = entries[scene.id]
                audio = directory / audio_entry.relative_path
                if not audio.is_file() or _sha256_file(audio) != audio_entry.audio_sha256:
                    raise RenderError(f"Narration cache is missing or corrupt for {scene.id}")
                effect = EFFECTS[index % len(EFFECTS)]
                digest = hashlib.sha256()
                for value in (scene.model_dump_json(), audio_entry.audio_sha256, source_hash,
                              effect, SCENE_RENDER_VERSION, self.scene_renderer.motion.cache_key,
                              f"{TARGET_WIDTH}x{TARGET_HEIGHT}@{TARGET_FPS}"):
                    digest.update(value.encode("utf-8"))
                fingerprint = f"sha256:{digest.hexdigest()}"
                output = directory / "scenes" / f"{scene.id}.mp4"
                prior = prior_scenes.get(scene.id)
                if prior and prior.fingerprint == fingerprint and output.is_file():
                    item = prior
                else:
                    item = self.scene_renderer.render(
                        scene, image=image, audio=audio, output=output,
                        width=TARGET_WIDTH, height=TARGET_HEIGHT, fps=TARGET_FPS,
                        duration=audio_entry.duration_seconds, fingerprint=fingerprint,
                        source_path=source_path, audio_path=audio_entry.relative_path,
                        effect=effect,
                    )
                rendered.append(item)
            scene_stage = _scene_list_fingerprint(rendered)
            atomic_write_model(manifest_path, SceneManifest(fingerprint=scene_stage,
                                                            scenes=rendered))
            store.update(PipelineStage.SCENES, StageStatus.COMPLETED, fingerprint=scene_stage,
                         metadata={"scene_count": len(rendered),
                                   "renderers": sorted({item.renderer for item in rendered})})
        except Exception as exc:
            store.update(PipelineStage.SCENES, StageStatus.FAILED,
                         error=f"{type(exc).__name__}: {exc}")
            raise
        preview_digest = hashlib.sha256()
        for value in (_scene_list_fingerprint(rendered), transition.model_dump_json(),
                      self.assembler.cache_key):
            preview_digest.update(value.encode("utf-8"))
        return directory, storyboard, rendered, article_assets, f"sha256:{preview_digest.hexdigest()}"

    def _resolve_visual(self, scene: object, index: int, directory: Path,
                        images: ImageManifest, generated_by_scene: dict[str, object],
                        acquired: dict[str, tuple[Path, ImageAsset]],
                        ) -> tuple[Path | None, str, str, ImageAsset | None]:
        if scene.type in MOTION_TYPES or scene.visual.type in MOTION_TYPES:  # type: ignore[attr-defined]
            return None, "motion-generated", self.scene_renderer.motion.cache_key, None
        provenance = scene.visual.provenance  # type: ignore[attr-defined]
        if provenance.source_type is SourceType.GENERATED:
            generated = generated_by_scene.get(scene.id)  # type: ignore[attr-defined]
            if generated is None:
                raise RenderError(f"Generated visual is missing for {scene.id}")  # type: ignore[attr-defined]
            path = directory / generated.relative_path
            if not path.is_file() or _sha256_file(path) != generated.content_sha256:
                raise RenderError(f"Generated visual is missing or corrupt for {scene.id}")  # type: ignore[attr-defined]
            return path, generated.relative_path, generated.content_sha256, None
        preferred = str(provenance.source_url) if provenance.source_type is SourceType.ARTICLE else ""
        fallback = str(images.images[index % len(images.images)].source_url) if images.images else ""
        url = preferred or fallback
        if not url:
            raise RenderError(f"No source image is available for {scene.id}")  # type: ignore[attr-defined]
        if url not in acquired:
            acquired[url] = self.image_cache.acquire(url, directory / "cache" / "images")
        path, asset = acquired[url]
        return path, str(path.relative_to(directory)).replace("\\", "/"), asset.sha256, asset

    @staticmethod
    def _article_assets(directory: Path, scenes: list[RenderedScene]) -> list[ImageAsset]:
        assets: list[ImageAsset] = []
        for scene in scenes:
            source = directory / scene.source_path
            if not scene.source_path.startswith("cache/images/") or not source.is_file():
                continue
            metadata = source.with_suffix(".json")
            # Phase 7 metadata is keyed by source URL rather than image filename; assets
            # are already optional in the Phase 10 manifest, so skip unavailable records.
            if metadata.is_file():
                try:
                    assets.append(load_model(metadata, ImageAsset))
                except (OSError, ValueError):
                    pass
        return assets

    @staticmethod
    def _validate_target(probe: object, label: str) -> None:
        if (probe.width, probe.height) != (TARGET_WIDTH, TARGET_HEIGHT):
            raise RenderError(f"{label} resolution must be 1080x1920")
        if abs(probe.fps - TARGET_FPS) > 0.01:
            raise RenderError(f"{label} frame rate must be 30fps")
        if probe.video_codec != "h264" or probe.audio_codec != "aac":
            raise RenderError(f"{label} codecs must be H.264 video and AAC audio")


def _scene_list_fingerprint(scenes: list[RenderedScene]) -> str:
    digest = hashlib.sha256()
    for scene in scenes:
        digest.update(scene.fingerprint.encode("ascii"))
    return f"sha256:{digest.hexdigest()}"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
