from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

import httpx

from newsvid_brain import FactSet, RenderError, Storyboard
from newsvid_brain.render_models import (ImageAsset, RenderManifest,
                                         RenderedScene, VideoProbe)
from newsvid_brain.tts_models import TTSManifest
from newsvid_ingest.models import ImageManifest
from newsvid_ingest.security import assert_public_http_url

from .checkpoint import CheckpointStore
from .persistence import atomic_write_model, atomic_write_text, load_model
from .project import ProjectManager
from .schemas import PipelineStage, StageStatus


EFFECTS = ("zoom_in", "zoom_out", "pan_left", "pan_right")
IMAGE_TYPES = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}


class ArticleImageCache:
    def __init__(self, *, max_bytes: int = 20 * 1024 * 1024,
                 transport: httpx.BaseTransport | None = None) -> None:
        self.max_bytes = max_bytes
        self.transport = transport

    def acquire(self, url: str, cache_dir: Path) -> tuple[Path, ImageAsset]:
        # Cached assets were already fetched from an ingestion-validated URL; avoid
        # a DNS dependency on cache hits, but revalidate DNS before network access.
        assert_public_http_url(url, resolve_dns=False)
        url_key = hashlib.sha256(url.encode("utf-8")).hexdigest()
        metadata_path = cache_dir / f"{url_key}.json"
        if metadata_path.is_file():
            try:
                asset = ImageAsset.model_validate_json(metadata_path.read_text(encoding="utf-8"))
                cached = cache_dir.parents[1] / asset.cache_path
                if cached.is_file() and _sha256_file(cached) == asset.sha256:
                    return cached, asset
            except (OSError, ValueError):
                pass
        assert_public_http_url(url)
        with httpx.Client(timeout=60, follow_redirects=True, transport=self.transport) as client:
            with client.stream("GET", url, headers={"User-Agent": "SuperVideoNewsvid/0.8"}) as response:
                response.raise_for_status()
                final_url = str(response.url)
                assert_public_http_url(final_url)
                content_type = response.headers.get("content-type", "").split(";", 1)[0].casefold()
                extension = IMAGE_TYPES.get(content_type)
                if extension is None:
                    raise RenderError(f"Unsupported article image content type: {content_type or 'missing'}")
                cache_dir.mkdir(parents=True, exist_ok=True)
                handle, temporary = tempfile.mkstemp(prefix=f".{url_key}.", suffix=".tmp", dir=cache_dir)
                size = 0
                digest = hashlib.sha256()
                try:
                    with os.fdopen(handle, "wb") as stream:
                        for chunk in response.iter_bytes():
                            size += len(chunk)
                            if size > self.max_bytes:
                                raise RenderError("Article image exceeds configured size limit")
                            digest.update(chunk)
                            stream.write(chunk)
                        stream.flush()
                        os.fsync(stream.fileno())
                    if size == 0:
                        raise RenderError("Article image response is empty")
                    output = cache_dir / f"{url_key}.{extension}"
                    os.replace(temporary, output)
                except BaseException:
                    Path(temporary).unlink(missing_ok=True)
                    raise
        asset = ImageAsset(source_url=final_url,
                           cache_path=f"cache/images/{output.name}",
                           sha256=digest.hexdigest(), content_type=content_type)
        atomic_write_model(metadata_path, asset)
        return output, asset


class FFmpegArticleRenderer:
    def __init__(self, *, ffmpeg: str = "ffmpeg", ffprobe: str = "ffprobe",
                 runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run) -> None:
        self.ffmpeg = ffmpeg
        self.ffprobe = ffprobe
        self.runner = runner

    def render_scene(self, image: Path, audio: Path, output: Path, *, duration: float,
                     width: int, height: int, fps: int, effect: str) -> Path:
        if not image.is_file() or not audio.is_file():
            raise RenderError(f"Missing scene input: image={image}, audio={audio}")
        frames = max(1, round(duration * fps))
        vf = self._ken_burns_filter(width, height, fps, frames, effect)
        output.parent.mkdir(parents=True, exist_ok=True)
        self._run([
            self.ffmpeg, "-y", "-loop", "1", "-i", str(image), "-i", str(audio),
            "-t", f"{duration:.6f}", "-vf", vf, "-c:v", "libx264", "-preset", "fast",
            "-crf", "23", "-pix_fmt", "yuv420p", "-r", str(fps),
            "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart",
            str(output),
        ], f"rendering scene {output.name}")
        return output

    def concatenate(self, scenes: list[Path], output: Path) -> Path:
        if not scenes or any(not scene.is_file() for scene in scenes):
            raise RenderError("All scene videos must exist before concatenation")
        concat_file = output.with_suffix(".concat.txt")
        # Paths are normalized and quotes escaped for FFmpeg concat syntax.
        lines = [f"file '{scene.resolve().as_posix().replace(chr(39), chr(39) + '\\' + chr(39) + chr(39))}'"
                 for scene in scenes]
        atomic_write_text(concat_file, "\n".join(lines))
        try:
            self._run([self.ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i",
                       str(concat_file), "-c", "copy", str(output)], "concatenating scenes")
        finally:
            concat_file.unlink(missing_ok=True)
        return output

    def burn_subtitles(self, video: Path, ass: Path, output: Path) -> Path:
        if not video.is_file() or not ass.is_file():
            raise RenderError("Video and ASS inputs are required")
        # Running from the caption directory avoids platform-specific filter escaping.
        self._run([self.ffmpeg, "-y", "-i", str(video.resolve()), "-vf", f"ass={ass.name}",
                   "-c:v", "libx264", "-preset", "fast", "-crf", "20",
                   "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart",
                   str(output.resolve())], "burning subtitles", cwd=ass.parent)
        return output

    def probe(self, video: Path) -> VideoProbe:
        result = self._run([
            self.ffprobe, "-v", "error", "-show_entries",
            "format=duration:stream=codec_type,codec_name,width,height", "-of", "json", str(video),
        ], "probing final video")
        try:
            payload = json.loads(result.stdout)
            video_stream = next(item for item in payload["streams"] if item["codec_type"] == "video")
            audio_stream = next(item for item in payload["streams"] if item["codec_type"] == "audio")
            return VideoProbe(width=video_stream["width"], height=video_stream["height"],
                              duration_seconds=float(payload["format"]["duration"]),
                              video_codec=video_stream["codec_name"],
                              audio_codec=audio_stream["codec_name"])
        except (KeyError, StopIteration, TypeError, ValueError) as exc:
            raise RenderError("Final MP4 does not contain valid video and audio streams") from exc

    def _ken_burns_filter(self, width: int, height: int, fps: int,
                          frames: int, effect: str) -> str:
        effect = effect if effect in EFFECTS else "zoom_in"
        expressions = {
            "zoom_in": ("min(zoom+0.0015,1.15)", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),
            "zoom_out": ("if(eq(on,0),1.15,max(zoom-0.0015,1.0))", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),
            "pan_left": ("1.12", f"(iw-iw/zoom)*(1-on/{frames})", "ih/2-(ih/zoom/2)"),
            "pan_right": ("1.12", f"(iw-iw/zoom)*on/{frames}", "ih/2-(ih/zoom/2)"),
        }
        zoom, x, y = expressions[effect]
        return (f"scale={width * 2}:{height * 2}:force_original_aspect_ratio=increase,"
                f"crop={width * 2}:{height * 2},"
                f"zoompan=z='{zoom}':x='{x}':y='{y}':d={frames}:s={width}x{height}:fps={fps},"
                "setsar=1,format=yuv420p")

    def _run(self, command: list[str], operation: str, **kwargs: object) -> subprocess.CompletedProcess[str]:
        try:
            return self.runner(command, check=True, capture_output=True, text=True,
                               shell=False, **kwargs)
        except (OSError, subprocess.CalledProcessError) as exc:
            stderr = getattr(exc, "stderr", "") or str(exc)
            raise RenderError(f"FFmpeg failed while {operation}: {stderr.strip()}") from exc


class ArticleVideoCoordinator:
    def __init__(self, projects: ProjectManager, image_cache: ArticleImageCache,
                 renderer: FFmpegArticleRenderer) -> None:
        self.projects = projects
        self.image_cache = image_cache
        self.renderer = renderer

    def render(self, project_id: str) -> RenderManifest:
        directory = self.projects.project_dir(project_id)
        self.projects.load(project_id)
        storyboard = load_model(directory / "storyboard.json", Storyboard)
        facts = load_model(directory / "facts.json", FactSet)
        fact_ids = {fact.id for fact in facts.facts}
        unresolved = sorted({ref for scene in storyboard.scenes for ref in scene.fact_refs
                             if ref not in fact_ids})
        if unresolved:
            raise RenderError(f"Storyboard contains unresolved fact references: {', '.join(unresolved)}")
        images = load_model(directory / "images.json", ImageManifest)
        tts = load_model(directory / "audio" / "tts_manifest.json", TTSManifest)
        ass_path = directory / "captions" / "subtitles.ass"
        if not ass_path.is_file() or not images.images:
            raise RenderError("Article images and Phase 6 ASS subtitles are required")
        entries = {entry.scene_id: entry for entry in tts.entries}
        if set(entries) != {scene.id for scene in storyboard.scenes}:
            raise RenderError("TTS manifest does not cover every storyboard scene")
        digest = hashlib.sha256()
        for value in (storyboard.model_dump_json(), facts.model_dump_json(), images.model_dump_json(),
                      tts.model_dump_json(), _sha256_file(ass_path)):
            digest.update(value.encode("utf-8"))
        fingerprint = f"sha256:{digest.hexdigest()}"
        manifest_path = directory / "output" / "render_manifest.json"
        final_path = directory / "output" / "article-video.mp4"
        store = CheckpointStore(directory / "checkpoint.json")
        previous = store.load().stages[PipelineStage.FINAL_RENDER]
        if previous.status is StageStatus.COMPLETED and previous.fingerprint == fingerprint:
            try:
                cached = load_model(manifest_path, RenderManifest)
                if final_path.is_file() and cached.fingerprint == fingerprint:
                    return cached
            except (OSError, ValueError):
                pass
        try:
            prior_scenes: dict[str, RenderedScene] = {}
            try:
                prior_scenes = {item.scene_id: item for item in
                                load_model(manifest_path, RenderManifest).scenes}
            except (OSError, ValueError):
                pass
            store.update(PipelineStage.VISUALS, StageStatus.RUNNING, fingerprint=fingerprint)
            cache_dir = directory / "cache" / "images"
            acquired: dict[str, tuple[Path, ImageAsset]] = {}
            assets: list[ImageAsset] = []
            for item in images.images:
                url = str(item.source_url)
                path, asset = self.image_cache.acquire(url, cache_dir)
                acquired[url] = (path, asset)
                assets.append(asset)
            store.update(PipelineStage.VISUALS, StageStatus.COMPLETED, fingerprint=fingerprint,
                         metadata={"asset_count": len(assets), "comfyui_used": False})
            store.update(PipelineStage.SCENES, StageStatus.RUNNING, fingerprint=fingerprint)
            rendered: list[RenderedScene] = []
            scene_paths: list[Path] = []
            for index, scene in enumerate(storyboard.scenes):
                preferred = str(scene.visual.provenance.source_url) if scene.visual.provenance.source_url else ""
                image, _asset = acquired.get(preferred, acquired[str(images.images[index % len(images.images)].source_url)])
                audio_entry = entries[scene.id]
                audio = directory / audio_entry.relative_path
                effect = EFFECTS[index % len(EFFECTS)]
                scene_digest = hashlib.sha256(
                    f"{fingerprint}|{scene.id}|{_sha256_file(image)}|{audio_entry.audio_sha256}|{effect}".encode()
                ).hexdigest()
                scene_fingerprint = f"sha256:{scene_digest}"
                output = directory / "scenes" / f"{scene.id}.mp4"
                prior = prior_scenes.get(scene.id)
                if not (prior and prior.fingerprint == scene_fingerprint and output.is_file()):
                    self.renderer.render_scene(image, audio, output,
                                               duration=audio_entry.duration_seconds,
                                               width=storyboard.video.width, height=storyboard.video.height,
                                               fps=storyboard.video.fps, effect=effect)
                scene_paths.append(output)
                rendered.append(RenderedScene(
                    scene_id=scene.id, image_path=str(image.relative_to(directory)).replace("\\", "/"),
                    audio_path=audio_entry.relative_path, video_path=f"scenes/{scene.id}.mp4",
                    effect=effect, duration_seconds=audio_entry.duration_seconds,
                    fingerprint=scene_fingerprint,
                ))
            store.update(PipelineStage.SCENES, StageStatus.COMPLETED, fingerprint=fingerprint,
                         metadata={"scene_count": len(rendered)})
            store.update(PipelineStage.PREVIEW, StageStatus.RUNNING, fingerprint=fingerprint)
            preview = directory / "output" / "article-video.preview.mp4"
            self.renderer.concatenate(scene_paths, preview)
            preview_probe = self.renderer.probe(preview)
            if preview_probe.width != storyboard.video.width or preview_probe.height != storyboard.video.height:
                raise RenderError("Preview resolution does not match storyboard")
            store.update(PipelineStage.PREVIEW, StageStatus.COMPLETED, fingerprint=fingerprint,
                         metadata={"output": "output/article-video.preview.mp4",
                                   "duration_seconds": preview_probe.duration_seconds})
            store.update(PipelineStage.FINAL_RENDER, StageStatus.RUNNING, fingerprint=fingerprint)
            self.renderer.burn_subtitles(preview, ass_path, final_path)
            probe = self.renderer.probe(final_path)
            if probe.width != storyboard.video.width or probe.height != storyboard.video.height:
                raise RenderError("Final video resolution does not match storyboard")
            manifest = RenderManifest(fingerprint=fingerprint, width=storyboard.video.width,
                                      height=storyboard.video.height, fps=storyboard.video.fps,
                                      scenes=rendered, assets=assets, probe=probe)
            atomic_write_model(manifest_path, manifest)
            store.update(PipelineStage.FINAL_RENDER, StageStatus.COMPLETED, fingerprint=fingerprint,
                         metadata={"output": manifest.output_path,
                                   "duration_seconds": probe.duration_seconds,
                                   "resolution": f"{probe.width}x{probe.height}"})
            return manifest
        except Exception as exc:
            store.update(PipelineStage.FINAL_RENDER, StageStatus.FAILED,
                         fingerprint=fingerprint, error=f"{type(exc).__name__}: {exc}")
            raise


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
