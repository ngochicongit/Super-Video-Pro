from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Callable

from newsvid_brain import (RenderError, RenderedScene, TransitionConfig,
                           TransitionType, VideoProbe)

from .persistence import atomic_write_text


ASSEMBLER_VERSION = "final-assembler-v1"
_DIALOGUE = re.compile(
    r"^(Dialogue:\s*[^,]*,)(\d+):(\d{2}):(\d{2}\.\d{2}),(\d+):(\d{2}):(\d{2}\.\d{2})(,.*)$"
)


class FinalAssembler:
    """The only boundary that combines RenderedScene files into preview/final MP4."""

    def __init__(self, *, ffmpeg: str = "ffmpeg", ffprobe: str = "ffprobe",
                 runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run) -> None:
        self.ffmpeg = ffmpeg
        self.ffprobe = ffprobe
        self.runner = runner

    @property
    def cache_key(self) -> str:
        return ASSEMBLER_VERSION

    def assemble_preview(self, scenes: list[RenderedScene], project_dir: Path, output: Path, *,
                         transition: TransitionConfig, width: int, height: int, fps: int,
                         subtitles: Path | None = None) -> Path:
        if not scenes:
            raise RenderError("At least one rendered scene is required for assembly")
        paths = [project_dir / scene.video_path for scene in scenes]
        if any(not path.is_file() for path in paths):
            raise RenderError("Every RenderedScene video must exist before assembly")
        effective = self._effective_transition(transition, scenes)
        command = [self.ffmpeg, "-y"]
        for path in paths:
            command.extend(["-i", str(path)])
        graph, video_label, audio_label = self._filter_graph(
            scenes, effective, width=width, height=height, fps=fps
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        encoded = output.with_suffix(".base.mp4") if subtitles is not None else output
        command.extend([
            "-filter_complex", graph, "-map", video_label, "-map", audio_label,
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-pix_fmt", "yuv420p", "-r", str(fps),
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            "-movflags", "+faststart", str(encoded),
        ])
        self._run(command, "assembling preview")
        if subtitles is not None:
            if not subtitles.is_file():
                encoded.unlink(missing_ok=True)
                raise RenderError("ASS subtitles are required for captioned preview")
            effective = self._effective_transition(transition, scenes)
            ass = subtitles
            if effective.type is not TransitionType.NONE and len(scenes) > 1:
                ass = subtitles.with_name("subtitles.final.ass")
                self._retime_ass(subtitles, ass, scenes, effective.duration_seconds)
            try:
                self._burn_subtitles(encoded, ass, output)
            finally:
                encoded.unlink(missing_ok=True)
        return output

    def finalize(self, preview: Path, output: Path) -> Path:
        if not preview.is_file():
            raise RenderError("Validated preview is required for final encoding")
        try:
            self._run([
                self.ffmpeg, "-y", "-i", str(preview.resolve()), "-c", "copy",
                "-movflags", "+faststart", str(output.resolve()),
            ], "finalizing validated video")
        except Exception:
            output.unlink(missing_ok=True)
            raise
        return output

    def _burn_subtitles(self, video: Path, ass: Path, output: Path) -> None:
        # Run from the caption directory to avoid platform-specific ASS filter escaping.
        self._run([
            self.ffmpeg, "-y", "-i", str(video.resolve()), "-vf", f"ass={ass.name}",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart",
            str(output.resolve()),
        ], "burning preview subtitles", cwd=ass.parent)

    def probe(self, video: Path) -> VideoProbe:
        result = self._run([
            self.ffprobe, "-v", "error", "-show_entries",
            "format=duration:stream=codec_type,codec_name,width,height,r_frame_rate",
            "-of", "json", str(video),
        ], "probing assembled video")
        try:
            payload = json.loads(result.stdout)
            video_stream = next(item for item in payload["streams"] if item["codec_type"] == "video")
            audio_stream = next(item for item in payload["streams"] if item["codec_type"] == "audio")
            numerator, denominator = video_stream["r_frame_rate"].split("/", 1)
            rate = float(numerator) / float(denominator)
            return VideoProbe(width=video_stream["width"], height=video_stream["height"],
                              duration_seconds=float(payload["format"]["duration"]),
                              video_codec=video_stream["codec_name"],
                              audio_codec=audio_stream["codec_name"], fps=rate)
        except (KeyError, StopIteration, TypeError, ValueError, ZeroDivisionError) as exc:
            raise RenderError("Assembled MP4 does not contain valid video/audio metadata") from exc

    @staticmethod
    def _effective_transition(config: TransitionConfig,
                              scenes: list[RenderedScene]) -> TransitionConfig:
        if config.type is TransitionType.NONE or len(scenes) < 2:
            return TransitionConfig(type=TransitionType.NONE, duration_seconds=0)
        maximum = min(scene.duration_seconds for scene in scenes) / 2
        return TransitionConfig(type=config.type,
                                duration_seconds=min(config.duration_seconds, maximum))

    @staticmethod
    def _filter_graph(scenes: list[RenderedScene], transition: TransitionConfig, *,
                      width: int, height: int, fps: int) -> tuple[str, str, str]:
        filters: list[str] = []
        for index in range(len(scenes)):
            filters.append(
                f"[{index}:v]settb=AVTB,setpts=PTS-STARTPTS,fps={fps},"
                f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black,"
                f"setsar=1,format=yuv420p[v{index}]"
            )
            filters.append(
                f"[{index}:a]aresample=48000,asetpts=PTS-STARTPTS,"
                "aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo"
                f"[a{index}]"
            )
        if len(scenes) == 1:
            return ";".join(filters), "[v0]", "[a0]"
        if transition.type is TransitionType.NONE:
            labels = "".join(f"[v{i}][a{i}]" for i in range(len(scenes)))
            filters.append(f"{labels}concat=n={len(scenes)}:v=1:a=1[vout][aout]")
            return ";".join(filters), "[vout]", "[aout]"
        duration = transition.duration_seconds
        cumulative = scenes[0].duration_seconds
        video_label = "v0"
        audio_label = "a0"
        for index in range(1, len(scenes)):
            offset = max(0, cumulative - duration)
            next_video = "vout" if index == len(scenes) - 1 else f"vx{index}"
            next_audio = "aout" if index == len(scenes) - 1 else f"ax{index}"
            filters.append(
                f"[{video_label}][v{index}]xfade=transition={transition.type.value}:"
                f"duration={duration:.3f}:offset={offset:.3f}[{next_video}]"
            )
            filters.append(
                f"[{audio_label}][a{index}]acrossfade=d={duration:.3f}:c1=tri:c2=tri[{next_audio}]"
            )
            video_label, audio_label = next_video, next_audio
            cumulative += scenes[index].duration_seconds - duration
        return ";".join(filters), f"[{video_label}]", f"[{audio_label}]"

    @staticmethod
    def _retime_ass(source: Path, output: Path, scenes: list[RenderedScene], overlap: float) -> None:
        boundaries: list[float] = []
        elapsed = 0.0
        for scene in scenes[:-1]:
            elapsed += scene.duration_seconds
            boundaries.append(elapsed)

        def shifted(value: float) -> float:
            return max(0, value - overlap * sum(value >= boundary for boundary in boundaries))

        lines: list[str] = []
        for line in source.read_text(encoding="utf-8-sig").splitlines():
            match = _DIALOGUE.match(line)
            if not match:
                lines.append(line)
                continue
            start = int(match[2]) * 3600 + int(match[3]) * 60 + float(match[4])
            end = int(match[5]) * 3600 + int(match[6]) * 60 + float(match[7])
            lines.append(
                f"{match[1]}{_ass_time(shifted(start))},{_ass_time(shifted(end))}{match[8]}"
            )
        atomic_write_text(output, "\n".join(lines))

    def _run(self, command: list[str], operation: str,
             **kwargs: object) -> subprocess.CompletedProcess[str]:
        try:
            return self.runner(command, check=True, capture_output=True, text=True,
                               shell=False, **kwargs)
        except (OSError, subprocess.CalledProcessError) as exc:
            stderr = getattr(exc, "stderr", "") or str(exc)
            raise RenderError(f"FFmpeg failed while {operation}: {stderr.strip()}") from exc


def _ass_time(seconds: float) -> str:
    centiseconds = max(0, round(seconds * 100))
    hours, remainder = divmod(centiseconds, 360000)
    minutes, remainder = divmod(remainder, 6000)
    whole, fraction = divmod(remainder, 100)
    return f"{hours}:{minutes:02d}:{whole:02d}.{fraction:02d}"
