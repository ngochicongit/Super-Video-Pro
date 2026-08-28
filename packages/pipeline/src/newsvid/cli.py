from __future__ import annotations

import argparse
import json
from pathlib import Path

from .checkpoint import CheckpointStore
from .config import load_config
from .doctor import collect_status
from .project import ProjectManager
from .schemas import PipelineStage, StageStatus
from .ingestion import IngestionCoordinator
from newsvid_ingest.errors import ArticleExtractionError
from newsvid_brain import (AlignmentError, F5TTSConfig, F5TTSProvider, LLMError, NewsStyle,
                           OllamaConfig, OllamaProvider, PiperConfig, PiperProvider,
                           RenderError, SubtitleLayout, TTSError, TransitionConfig, TransitionType,
                           WhisperXConfig, WhisperXProvider,
                           load_pronunciation)
from .facts import FactsCoordinator
from .scripts import ScriptCoordinator
from .storyboards import StoryboardCoordinator
from .tts import TTSCoordinator
from .alignment import AlignmentCoordinator
from .article_renderer import ArticleImageCache, FFmpegArticleRenderer
from .motion_renderer import HyperFramesChromiumRenderer, SceneRenderer
from .final_assembler import FinalAssembler
from .video_renderer import VideoRenderCoordinator
from .comfyui import HTTPComfyUIProvider
from .visuals import VisualCoordinator


def _print_model(model: object) -> None:
    payload = model.model_dump(mode="json")  # type: ignore[attr-defined]
    print(json.dumps(payload, ensure_ascii=True, indent=2))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="newsvid", description="AI News Video local pipeline")
    parser.add_argument("--config", type=Path, help="Path to app.yaml")
    commands = parser.add_subparsers(dest="command", required=True)
    doctor = commands.add_parser("doctor", help="Report local dependencies")
    doctor.add_argument("--strict", action="store_true", help="Fail when a required dependency is unavailable")
    ingest = commands.add_parser("ingest", help="Extract an article into a project")
    ingest.add_argument("source", help="Public HTTP(S) URL or local HTML fixture")
    ingest.add_argument("--project", dest="project_id", help="Existing project id")
    ingest.add_argument("--name", help="Name for a newly created project")
    ingest.add_argument("--source-url", default="https://fixture.invalid/article", help="Canonical URL used with a local fixture")
    ingest.add_argument("--no-browser-fallback", action="store_true")
    facts = commands.add_parser("facts", help="Extract grounded facts from article.md")
    facts.add_argument("project_id")
    script = commands.add_parser("script", help="Generate a Vietnamese news script from facts.json")
    script.add_argument("project_id")
    script.add_argument("--duration", type=int, default=60, choices=range(30, 91), metavar="30-90")
    script.add_argument("--style", choices=[style.value for style in NewsStyle],
                        default=NewsStyle.BREAKING_NEWS.value)
    storyboard = commands.add_parser("storyboard", help="Build the editable visual storyboard")
    storyboard.add_argument("project_id")
    tts = commands.add_parser("tts", help="Generate cached Vietnamese WAV narration")
    tts.add_argument("project_id")
    tts.add_argument("--provider", choices=["piper", "f5tts"])
    tts.add_argument("--voice")
    align = commands.add_parser("align", help="Align Vietnamese narration and generate ASS subtitles")
    align.add_argument("project_id")
    visuals = commands.add_parser("visuals", help="Generate optional ComfyUI storyboard visuals")
    visuals.add_argument("project_id")
    for command_name, help_text in (
        ("render", "Render the complete 1080x1920 video"),
        ("preview", "Assemble a caption-free 1080x1920 preview"),
        ("render-article", "Compatibility alias for the unified final renderer"),
    ):
        render = commands.add_parser(command_name, help=help_text)
        render.add_argument("project_id")
        render.add_argument("--transition", choices=[item.value for item in TransitionType],
                            default=TransitionType.FADE.value)
        render.add_argument("--transition-duration", type=float, default=.35)
    project = commands.add_parser("project", help="Manage Phase 0 projects")
    project_commands = project.add_subparsers(dest="project_command", required=True)
    create = project_commands.add_parser("create", help="Create a project")
    create.add_argument("name")
    inspect = project_commands.add_parser("inspect", help="Inspect a project")
    inspect.add_argument("project_id")
    checkpoint = commands.add_parser("checkpoint", help="Inspect or update a project checkpoint")
    checkpoint_commands = checkpoint.add_subparsers(dest="checkpoint_command", required=True)
    show = checkpoint_commands.add_parser("show")
    show.add_argument("project_id")
    update = checkpoint_commands.add_parser("set")
    update.add_argument("project_id")
    update.add_argument("stage", choices=[stage.value for stage in PipelineStage])
    update.add_argument("status", choices=[status.value for status in StageStatus])
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    config = load_config(args.config)
    manager = ProjectManager(config.projects_dir)
    if args.command == "doctor":
        statuses = collect_status(config)
        for item in statuses:
            print(f"{item.name:<12} {item.status:<16} {item.detail}")
        return 1 if args.strict and any(item.required and item.status != "OK" for item in statuses) else 0
    if args.command == "ingest":
        coordinator = IngestionCoordinator(manager)
        try:
            source_path = Path(args.source)
            if source_path.is_file():
                project = coordinator.ingest_file(source_path, source_url=args.source_url, project_id=args.project_id, name=args.name)
            else:
                project = coordinator.ingest_url(args.source, project_id=args.project_id, name=args.name, browser_fallback=not args.no_browser_fallback)
        except (ArticleExtractionError, OSError, ValueError) as exc:
            print(f"INGEST ERROR: {exc}")
            return 2
        _print_model(project)
        return 0
    if args.command == "facts":
        provider = OllamaProvider(OllamaConfig(
            base_url=config.services.ollama_url,
            model=config.services.ollama_model,
            temperature=config.services.ollama_temperature,
            timeout_seconds=config.services.ollama_timeout_seconds,
            max_attempts=config.services.ollama_max_attempts,
        ))
        try:
            result = FactsCoordinator(manager, provider).extract(args.project_id)
        except (LLMError, OSError, ValueError) as exc:
            print(f"FACTS ERROR: {exc}")
            return 2
        _print_model(result)
        return 0
    if args.command == "script":
        provider = OllamaProvider(OllamaConfig(
            base_url=config.services.ollama_url,
            model=config.services.ollama_model,
            temperature=config.services.ollama_temperature,
            timeout_seconds=config.services.ollama_timeout_seconds,
            max_attempts=config.services.ollama_max_attempts,
        ))
        try:
            result = ScriptCoordinator(manager, provider).generate(
                args.project_id, target_duration=args.duration, style=NewsStyle(args.style)
            )
        except (LLMError, OSError, ValueError) as exc:
            print(f"SCRIPT ERROR: {exc}")
            return 2
        _print_model(result)
        return 0
    if args.command == "storyboard":
        try:
            result = StoryboardCoordinator(manager).build(args.project_id)
        except (LLMError, OSError, ValueError) as exc:
            print(f"STORYBOARD ERROR: {exc}")
            return 2
        _print_model(result)
        return 0
    if args.command == "tts":
        provider_name = args.provider or config.services.tts_provider
        voice = args.voice or config.services.tts_voice
        if provider_name == "piper":
            provider = PiperProvider(PiperConfig(
                executable=config.services.piper_executable,
                model_path=config.services.piper_model_path,
                voice_name=voice,
                speed=config.services.tts_speed,
                timeout_seconds=config.services.tts_timeout_seconds,
            ))
        else:
            provider = F5TTSProvider(F5TTSConfig(
                base_url=config.services.f5tts_url,
                speed=config.services.tts_speed,
                timeout_seconds=config.services.tts_timeout_seconds,
            ))
        try:
            result = TTSCoordinator(manager, provider, load_pronunciation(config.pronunciation_path),
                                    voice=voice).generate(args.project_id)
        except (TTSError, OSError, ValueError) as exc:
            print(f"TTS ERROR: {exc}")
            return 2
        _print_model(result)
        return 0
    if args.command == "align":
        provider = WhisperXProvider(WhisperXConfig(
            base_url=config.services.whisperx_url,
            model=config.services.whisperx_model,
            timeout_seconds=config.services.whisperx_timeout_seconds,
        ))
        layout = SubtitleLayout(
            top_safe_px=config.services.subtitle_top_safe_px,
            bottom_safe_px=config.services.subtitle_bottom_safe_px,
            max_words_per_line=config.services.subtitle_max_words_per_line,
        )
        try:
            words, report = AlignmentCoordinator(manager, provider, layout).generate(args.project_id)
        except (AlignmentError, OSError, ValueError) as exc:
            print(f"ALIGNMENT ERROR: {exc}")
            return 2
        _print_model(words)
        print(json.dumps(report.model_dump(mode="json"), ensure_ascii=True, indent=2))
        return 0
    if args.command == "visuals":
        provider = HTTPComfyUIProvider(
            base_url=config.services.comfyui_url,
            checkpoint=config.services.comfyui_checkpoint,
            workflow_dir=config.services.comfyui_workflow_dir,
            timeout_seconds=config.services.comfyui_timeout_seconds,
            poll_interval_seconds=config.services.comfyui_poll_interval_seconds,
        )
        result = VisualCoordinator(manager, provider).generate(args.project_id)
        _print_model(result)
        return 2 if result.failures else 0
    if args.command in {"render", "preview", "render-article"}:
        try:
            repository_root = Path.cwd() if (Path.cwd() / "package.json").is_file() else Path(__file__).resolve().parents[4]
            ffmpeg_renderer = FFmpegArticleRenderer(ffmpeg=config.services.ffmpeg_executable,
                                                    ffprobe=config.services.ffprobe_executable)
            motion_renderer = HyperFramesChromiumRenderer(
                repository_root=repository_root,
                node=config.services.node_executable, ffmpeg=config.services.ffmpeg_executable,
                chromium=config.services.chromium_executable,
            )
            coordinator = VideoRenderCoordinator(
                manager, ArticleImageCache(max_bytes=config.services.image_max_bytes),
                SceneRenderer(ffmpeg_renderer, motion_renderer),
                FinalAssembler(ffmpeg=config.services.ffmpeg_executable,
                               ffprobe=config.services.ffprobe_executable),
            )
            transition = TransitionConfig(type=TransitionType(args.transition),
                                          duration_seconds=args.transition_duration)
            result = (coordinator.preview(args.project_id, transition=transition)
                      if args.command == "preview"
                      else coordinator.render(args.project_id, transition=transition))
        except (RenderError, OSError, ValueError) as exc:
            print(f"RENDER ERROR: {exc}")
            return 2
        _print_model(result)
        return 0
    if args.command == "project" and args.project_command == "create":
        project = manager.create(args.name)
        _print_model(project)
        return 0
    if args.command == "project" and args.project_command == "inspect":
        _print_model(manager.load(args.project_id))
        return 0
    store = CheckpointStore(manager.project_dir(args.project_id) / "checkpoint.json")
    if args.checkpoint_command == "set":
        checkpoint = store.update(PipelineStage(args.stage), StageStatus(args.status))
    else:
        checkpoint = store.load()
    _print_model(checkpoint)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
