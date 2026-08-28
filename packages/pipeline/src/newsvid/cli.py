from __future__ import annotations

import argparse
import json
from pathlib import Path

from .checkpoint import CheckpointStore
from .config import load_config
from .doctor import collect_status
from .project import ProjectManager
from .schemas import PipelineStage, StageStatus


def _print_model(model: object) -> None:
    payload = model.model_dump(mode="json")  # type: ignore[attr-defined]
    print(json.dumps(payload, ensure_ascii=True, indent=2))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="newsvid", description="AI News Video local pipeline")
    parser.add_argument("--config", type=Path, help="Path to app.yaml")
    commands = parser.add_subparsers(dest="command", required=True)
    doctor = commands.add_parser("doctor", help="Report local dependencies")
    doctor.add_argument("--strict", action="store_true", help="Fail when a required dependency is unavailable")
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
