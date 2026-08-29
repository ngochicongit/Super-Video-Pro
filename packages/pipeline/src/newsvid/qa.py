from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from newsvid_brain import FactSet, RenderManifest, Storyboard
from newsvid_ingest.models import ImageManifest

from .final_assembler import FinalAssembler
from .persistence import atomic_write_text, load_model
import json
from .project import ProjectManager


class QACoordinator:
    def __init__(self, projects: ProjectManager, assembler: FinalAssembler) -> None:
        self.projects, self.assembler = projects, assembler

    def run(self, project_id: str) -> dict[str, Any]:
        root = self.projects.project_dir(project_id)
        checks: list[dict[str, Any]] = []
        def check(name: str, ok: bool, detail: str = "") -> None:
            checks.append({"name": name, "status": "pass" if ok else "fail", "detail": detail})
        errors: list[str] = []
        try:
            board = load_model(root / "storyboard.json", Storyboard)
            facts = load_model(root / "facts.json", FactSet)
            fact_ids = {f.id for f in facts.facts}
            bad = sorted({ref for s in board.scenes for ref in s.fact_refs if ref not in fact_ids})
            check("fact_references", not bad, ", ".join(bad)); errors += [f"unresolved facts: {bad}"] if bad else []
            durations = [s.duration_seconds for s in board.scenes]
            invalid_durations = [s.id for s in board.scenes if s.duration_seconds <= 0]
            check("scene_duration", not invalid_durations, ", ".join(invalid_durations))
            images = load_model(root / "images.json", ImageManifest)
            urls = [str(i.source_url) for i in images.images]
            duplicated = sorted({url for url in urls if urls.count(url) > 1})
            check("duplicate_visuals", not duplicated, ", ".join(duplicated))
        except Exception as exc:
            check("project_inputs", False, str(exc)); errors.append(str(exc)); board = None
        manifest_path = root / "output" / "render_manifest.json"
        preview_path = root / "output" / "preview.mp4"
        if manifest_path.is_file():
            try:
                manifest = load_model(manifest_path, RenderManifest)
                for scene in manifest.scenes:
                    path = root / scene.video_path
                    check(f"scene:{scene.scene_id}", path.is_file() and path.stat().st_size > 0, "missing or blank scene")
                probe = manifest.probe
                check("resolution", (probe.width, probe.height) == (1080, 1920), f"{probe.width}x{probe.height}")
                check("fps", abs(probe.fps - 30) < .01, str(probe.fps))
                check("audio", probe.audio_codec == "aac", probe.audio_codec)
                check("ffmpeg_render", (root / manifest.output_path).is_file(), "final output missing")
            except Exception as exc:
                check("render_output", False, str(exc)); errors.append(str(exc))
        elif preview_path.is_file():
            try:
                probe = self.assembler.probe(preview_path)
                check("preview_output", True, "Đã kiểm tra bản xem trước; chưa kết xuất video hoàn chỉnh")
                check("resolution", (probe.width, probe.height) == (1080, 1920), f"{probe.width}x{probe.height}")
                check("fps", abs(probe.fps - 30) < .01, str(probe.fps))
                check("audio", probe.audio_codec == "aac", probe.audio_codec)
                checks.append({"name": "final_render", "status": "not_run", "detail": "Chưa tạo video hoàn chỉnh"})
            except Exception as exc:
                check("preview_output", False, str(exc)); errors.append(str(exc))
        else:
            detail = "Chưa có bản xem trước hoặc video hoàn chỉnh. Hãy tạo preview trước khi kiểm tra."
            check("render_output", False, detail); errors.append(detail)
        report = {"schema_version": 1, "project_id": project_id, "status": "fail" if errors or any(c["status"] == "fail" for c in checks) else "pass", "checks": checks, "errors": errors}
        atomic_write_text(root / "qa.json", json.dumps(report, ensure_ascii=True, indent=2))
        return report
