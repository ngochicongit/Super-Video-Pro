from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Callable

from newsvid_brain import RenderError, RenderedScene, StoryboardScene
from newsvid_brain.motion_models import MotionRenderResult, MotionTemplate, MotionTemplateInput
from newsvid_brain.motion_templates import TEMPLATE_VERSION, render_motion_html
from newsvid_brain.storyboard_models import SceneType

from .persistence import atomic_write_text


MOTION_TYPES = {
    SceneType.HOOK: MotionTemplate.HOOK,
    SceneType.HEADLINE: MotionTemplate.HEADLINE,
    SceneType.KINETIC_TEXT: MotionTemplate.HOOK,
    SceneType.STAT_HERO: MotionTemplate.STAT_HERO,
    SceneType.CHART: MotionTemplate.CHART,
    SceneType.COMPARISON: MotionTemplate.COMPARISON,
    SceneType.TIMELINE: MotionTemplate.TIMELINE,
    SceneType.QUOTE: MotionTemplate.QUOTE,
    SceneType.OUTRO: MotionTemplate.OUTRO,
}


def motion_input_for_scene(scene: StoryboardScene, *, width: int, height: int,
                           fps: int, duration: float) -> MotionTemplateInput:
    template = MOTION_TYPES.get(scene.type) or MOTION_TYPES.get(scene.visual.type)
    if template is None:
        raise RenderError(f"Scene {scene.id} is not a supported motion-graphics scene")
    source = dict(scene.visual.data)
    narration = scene.narration
    if template in {MotionTemplate.HOOK, MotionTemplate.HEADLINE}:
        data = {"headline": source.get("headline") or source.get("title") or narration,
                "subhead": source.get("subhead") or "Bản tin Việt Nam"}
    elif template is MotionTemplate.STAT_HERO:
        numbers = _numbers(narration)
        data = {"value": source.get("value") or (numbers[0] if numbers else "—"),
                "label": source.get("label") or narration,
                "context": source.get("context") or "Nguồn bài viết"}
    elif template is MotionTemplate.CHART:
        raw = source.get("data")
        if not isinstance(raw, list):
            values = source.get("values") if isinstance(source.get("values"), list) else _numbers(narration)
            raw = [{"label": f"Mốc {index}", "value": _numeric(value)}
                   for index, value in enumerate(values[:8], 1)]
        if len(raw) < 2:
            raw = [{"label": "Hiện tại", "value": 1}, {"label": "Mục tiêu", "value": 2}]
        data = {"title": source.get("title") or narration, "data": raw[:8]}
    elif template is MotionTemplate.COMPARISON:
        values = source.get("values") if isinstance(source.get("values"), list) else _numbers(narration)
        values = list(values) + ["—", "—"]
        data = {"left": source.get("left") or {"label": "Trước", "value": values[0]},
                "right": source.get("right") or {"label": "Sau", "value": values[1]}}
    elif template is MotionTemplate.TIMELINE:
        items = source.get("items")
        if not isinstance(items, list):
            pieces = [part.strip() for part in re.split(r"[.;]", source.get("text") or narration) if part.strip()]
            items = [{"label": f"Mốc {index}", "text": text}
                     for index, text in enumerate((pieces or [narration])[:6], 1)]
        if len(items) < 2:
            items = [items[0], {"label": "Tiếp theo", "text": narration}]
        data = {"items": items[:6]}
    elif template is MotionTemplate.QUOTE:
        data = {"quote": source.get("quote") or narration,
                "author": source.get("author") or source.get("source") or "Nguồn bài viết"}
    else:
        data = {"headline": source.get("closing_text") or source.get("headline") or narration,
                "source": source.get("source") or "Theo dõi để xem thêm"}
    return MotionTemplateInput(template=template, duration_seconds=duration,
                               width=width, height=height, fps=fps, data=data)


class HyperFramesChromiumRenderer:
    """Thin adapter over html-video's Playwright/Chromium recording foundation."""

    engine = "html-video-playwright-hyperframes-adapter"

    def __init__(self, *, repository_root: Path, node: str = "node", ffmpeg: str = "ffmpeg",
                 chromium: Path | None = None,
                 runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run) -> None:
        self.root = repository_root.resolve()
        self.node = node
        self.ffmpeg = ffmpeg
        self.chromium = chromium or Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
        self.runner = runner
        self.script = self.root / "scripts" / "render-motion-scene.mjs"
        self.gsap = self.root / "node_modules" / "gsap" / "dist" / "gsap.min.js"
        packaged = Path(__file__).parent / "runtime"
        if not self.script.is_file():
            self.script = packaged / "render-motion-scene.mjs"
        if not self.gsap.is_file():
            self.gsap = packaged / "gsap.min.js"

    @property
    def cache_key(self) -> str:
        digest = hashlib.sha256()
        for path in (self.script, self.gsap):
            if not path.is_file():
                raise RenderError(f"Motion runtime dependency not found: {path}")
            digest.update(path.read_bytes())
        digest.update(TEMPLATE_VERSION.encode())
        return f"sha256:{digest.hexdigest()}"

    def render(self, spec: MotionTemplateInput, html_path: Path, output_path: Path) -> MotionRenderResult:
        if not self.chromium.is_file():
            raise RenderError(f"Chromium/Edge executable not found: {self.chromium}")
        html_source = render_motion_html(spec, self.gsap.read_text(encoding="utf-8"))
        fingerprint = "sha256:" + hashlib.sha256(
            (spec.model_dump_json() + self.cache_key).encode("utf-8")
        ).hexdigest()
        atomic_write_text(html_path, html_source)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        command = [self.node, str(self.script), "--html", str(html_path), "--output", str(output_path),
                   "--width", str(spec.width), "--height", str(spec.height), "--fps", str(spec.fps),
                   "--duration", str(spec.duration_seconds), "--ffmpeg", self.ffmpeg,
                   "--chromium", str(self.chromium)]
        try:
            result = self.runner(command, check=True, capture_output=True, text=True,
                                 shell=False, cwd=self.root, timeout=max(60, spec.duration_seconds * 5))
            metadata = json.loads(result.stdout)
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
            stderr = getattr(exc, "stderr", "") or str(exc)
            raise RenderError(f"Chromium motion render failed: {stderr.strip()}") from exc
        if not output_path.is_file() or metadata.get("engine") != self.engine:
            raise RenderError("Motion runtime did not produce a valid output")
        return MotionRenderResult(template=spec.template,
                                  html_path=str(html_path), video_path=str(output_path),
                                  fingerprint=fingerprint, duration_seconds=spec.duration_seconds,
                                  width=spec.width, height=spec.height)


class SceneRenderer:
    """Single scene boundary dispatching existing article or motion rendering."""

    def __init__(self, article_renderer: object, motion_renderer: HyperFramesChromiumRenderer) -> None:
        self.article = article_renderer
        self.motion = motion_renderer

    def render(self, scene: StoryboardScene, *, image: Path | None, audio: Path,
               output: Path, width: int, height: int, fps: int, duration: float,
               fingerprint: str, source_path: str, audio_path: str,
               effect: str = "zoom_in") -> RenderedScene:
        if scene.type in MOTION_TYPES or scene.visual.type in MOTION_TYPES:
            spec = motion_input_for_scene(scene, width=width, height=height, fps=fps, duration=duration)
            silent = output.with_suffix(".motion.mp4")
            html_path = output.with_suffix(".html")
            self.motion.render(spec, html_path, silent)
            try:
                self.article.mux_audio(silent, audio, output, duration=duration)
            finally:
                silent.unlink(missing_ok=True)
            renderer = self.motion.engine
        else:
            if image is None:
                raise RenderError(f"Image visual is required for scene {scene.id}")
            self.article.render_scene(image, audio, output, duration=duration,
                                      width=width, height=height, fps=fps, effect=effect)
            renderer = ("ffmpeg-ai-image" if scene.visual.provenance.generator == "comfyui"
                        else "ffmpeg-article-image")
        return RenderedScene(
            scene_id=scene.id, source_path=source_path, audio_path=audio_path,
            video_path=f"scenes/{scene.id}.mp4", effect=effect, renderer=renderer,
            duration_seconds=duration, fingerprint=fingerprint,
        )


def _numbers(text: str) -> list[str]:
    return re.findall(r"\d[\d.,]*(?:\s*%)?", text)


def _numeric(value: object) -> float:
    found = re.search(r"\d+(?:[.,]\d+)?", str(value).replace(".", ""))
    return float(found.group(0).replace(",", ".")) if found else 0
