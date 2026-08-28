from __future__ import annotations

import hashlib
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Callable
import httpx

from newsvid_brain import RenderError
from newsvid_brain.render_models import ImageAsset
from newsvid_ingest.security import assert_public_http_url

from .persistence import atomic_write_model


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

    def mux_audio(self, video: Path, audio: Path, output: Path, *, duration: float) -> Path:
        if not video.is_file() or not audio.is_file():
            raise RenderError("Motion video and narration audio are required")
        self._run([self.ffmpeg, "-y", "-i", str(video), "-i", str(audio),
                   "-t", f"{duration:.6f}", "-c:v", "copy", "-c:a", "aac",
                   "-b:a", "128k", "-shortest", "-movflags", "+faststart", str(output)],
                  f"muxing motion scene {output.name}")
        return output

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


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
