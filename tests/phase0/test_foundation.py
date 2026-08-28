from pathlib import Path

import pytest
from pydantic import ValidationError

from newsvid.checkpoint import CheckpointStore
from newsvid.project import PROJECT_DIRS, ProjectManager
from newsvid.schemas import Checkpoint, PipelineStage, StageStatus
from newsvid.cli import main
from newsvid.config import load_config
from newsvid.logging import configure_logging
import json
import logging


def test_project_creation_and_checkpoint_persistence(tmp_path: Path) -> None:
    manager = ProjectManager(tmp_path / "projects")
    project = manager.create("Tin công nghệ")
    directory = manager.project_dir(project.id)
    assert manager.load(project.id) == project
    assert all((directory / child).is_dir() for child in PROJECT_DIRS)
    store = CheckpointStore(directory / "checkpoint.json")
    updated = store.update(PipelineStage.INGEST, StageStatus.RUNNING, fingerprint="sha256:test")
    assert updated.stages[PipelineStage.INGEST].status is StageStatus.RUNNING
    assert store.load().stages[PipelineStage.INGEST].fingerprint == "sha256:test"


def test_checkpoint_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        Checkpoint.model_validate({"project_id": "valid", "unexpected": True})


def test_project_ids_cannot_escape_root(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        ProjectManager(tmp_path).project_dir("../escape")


def test_cli_round_trip_with_vietnamese_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("NEWSVID_PROJECTS_DIR", str(tmp_path / "projects"))
    assert main(["project", "create", "Bản tin thử nghiệm"]) == 0
    output = capsys.readouterr().out
    assert "B\\u1ea3n tin th\\u1eed nghi\\u1ec7m" in output


def test_phase0_provenance_documents_exist() -> None:
    root = Path(__file__).parents[2]
    required = [
        "MASTER_PLAN.md",
        "ARCHITECTURE.md",
        "THIRD_PARTY_NOTICES.md",
        "docs/UPSTREAM_REUSE_AUDIT.md",
        "docs/UPSTREAM_SOURCE_MAP.md",
        "licenses/upstream/Auto-Create-Video-MIT.txt",
        "licenses/upstream/html-video-Apache-2.0.txt",
        "licenses/upstream/UNLICENSED_REFERENCES.md",
    ]
    assert all((root / path).is_file() for path in required)


def test_config_override_and_structured_logging(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEWSVID_PROJECTS_DIR", str(tmp_path / "custom-projects"))
    config = load_config(Path(__file__).parents[2] / "config" / "app.yaml")
    assert config.projects_dir == tmp_path / "custom-projects"
    log_path = tmp_path / "events.jsonl"
    configure_logging("INFO", log_path)
    logging.getLogger("newsvid.phase0").info("project_created", extra={"event": "project.created"})
    record = json.loads(log_path.read_text(encoding="utf-8"))
    assert record["event"] == "project.created"
