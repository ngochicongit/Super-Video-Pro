from __future__ import annotations

import hashlib

from newsvid_brain import FactExtractor, FactSet, FactSource, LLMProvider
from newsvid_brain.prompts import PROMPT_VERSION
from newsvid_ingest.models import Source

from .checkpoint import CheckpointStore
from .persistence import atomic_write_model, load_model
from .project import ProjectManager
from .schemas import PipelineStage, StageStatus


class FactsCoordinator:
    def __init__(self, projects: ProjectManager, provider: LLMProvider) -> None:
        self.projects = projects
        self.provider = provider

    def extract(self, project_id: str) -> FactSet:
        directory = self.projects.project_dir(project_id)
        self.projects.load(project_id)
        article = (directory / "article.md").read_text(encoding="utf-8")
        source = load_model(directory / "source.json", Source)
        fact_source = FactSource(url=source.url, publisher=source.domain, title=source.title)
        digest = hashlib.sha256()
        for value in (article, source.model_dump_json(), PROMPT_VERSION, self.provider.cache_key):
            digest.update(value.encode("utf-8"))
        fingerprint = f"sha256:{digest.hexdigest()}"
        store = CheckpointStore(directory / "checkpoint.json")
        checkpoint = store.load().stages[PipelineStage.FACTS]
        facts_path = directory / "facts.json"
        if checkpoint.status is StageStatus.COMPLETED and checkpoint.fingerprint == fingerprint:
            try:
                return load_model(facts_path, FactSet)
            except (OSError, ValueError):
                pass
        store.update(PipelineStage.FACTS, StageStatus.RUNNING, fingerprint=fingerprint)
        try:
            facts = FactExtractor(self.provider).extract(article, fact_source)
            atomic_write_model(facts_path, facts)
            store.update(PipelineStage.FACTS, StageStatus.COMPLETED, fingerprint=fingerprint,
                         metadata={"fact_count": len(facts.facts), "prompt_version": PROMPT_VERSION,
                                   "provider": self.provider.cache_key})
            return facts
        except Exception as exc:
            store.update(PipelineStage.FACTS, StageStatus.FAILED, fingerprint=fingerprint,
                         error=f"{type(exc).__name__}: {exc}")
            raise
