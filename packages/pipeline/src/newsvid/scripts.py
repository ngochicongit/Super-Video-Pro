from __future__ import annotations

import hashlib

from newsvid_brain import FactSet, LLMProvider
from newsvid_brain.script_models import NewsScript, NewsStyle
from newsvid_brain.script_prompts import SCRIPT_PROMPT_VERSION
from newsvid_brain.script_service import ScriptGenerator

from .checkpoint import CheckpointStore
from .persistence import atomic_write_model, load_model
from .project import ProjectManager
from .schemas import PipelineStage, StageStatus


class ScriptCoordinator:
    def __init__(self, projects: ProjectManager, provider: LLMProvider) -> None:
        self.projects = projects
        self.provider = provider

    def generate(self, project_id: str, *, target_duration: int = 60,
                 style: NewsStyle = NewsStyle.BREAKING_NEWS) -> NewsScript:
        directory = self.projects.project_dir(project_id)
        self.projects.load(project_id)
        facts = load_model(directory / "facts.json", FactSet)
        digest = hashlib.sha256()
        for value in (facts.model_dump_json(), SCRIPT_PROMPT_VERSION, self.provider.cache_key,
                      style.value, str(target_duration)):
            digest.update(value.encode("utf-8"))
        fingerprint = f"sha256:{digest.hexdigest()}"
        store = CheckpointStore(directory / "checkpoint.json")
        checkpoint = store.load().stages[PipelineStage.SCRIPT]
        script_path = directory / "script.json"
        if checkpoint.status is StageStatus.COMPLETED and checkpoint.fingerprint == fingerprint:
            try:
                return load_model(script_path, NewsScript)
            except (OSError, ValueError):
                pass
        store.update(PipelineStage.SCRIPT, StageStatus.RUNNING, fingerprint=fingerprint)
        try:
            script = ScriptGenerator(self.provider).generate(
                facts, target_duration=target_duration, style=style
            )
            atomic_write_model(script_path, script)
            store.update(PipelineStage.SCRIPT, StageStatus.COMPLETED, fingerprint=fingerprint,
                         metadata={"style": style.value, "target_duration_seconds": target_duration,
                                   "estimated_duration_seconds": script.estimated_duration_seconds,
                                   "segment_count": len(script.segments),
                                   "prompt_version": SCRIPT_PROMPT_VERSION,
                                   "provider": self.provider.cache_key})
            return script
        except Exception as exc:
            store.update(PipelineStage.SCRIPT, StageStatus.FAILED, fingerprint=fingerprint,
                         error=f"{type(exc).__name__}: {exc}")
            raise
