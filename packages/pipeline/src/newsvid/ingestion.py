from __future__ import annotations

import hashlib
from pathlib import Path

from newsvid_ingest import ArticleIngestor, IngestResult

from .checkpoint import CheckpointStore
from .persistence import atomic_write_model, atomic_write_text
from .project import ProjectManager
from .schemas import PipelineStage, Project, StageStatus


class IngestionCoordinator:
    def __init__(self, projects: ProjectManager, ingestor: ArticleIngestor | None = None) -> None:
        self.projects = projects
        self.ingestor = ingestor or ArticleIngestor()

    def ingest_url(
        self,
        url: str,
        *,
        project_id: str | None = None,
        name: str | None = None,
        browser_fallback: bool = True,
    ) -> Project:
        project = self.projects.load(project_id) if project_id else None
        if project:
            self._checkpoint(project).update(PipelineStage.INGEST, StageStatus.RUNNING)
        try:
            result = self.ingestor.ingest_url(url, browser_fallback=browser_fallback)
            project = project or self.projects.create((name or result.article.source.title)[:120])
            return self._persist(project, result)
        except Exception as exc:
            if project:
                self._checkpoint(project).update(PipelineStage.INGEST, StageStatus.FAILED, error=str(exc))
            raise

    def ingest_file(
        self,
        path: Path,
        *,
        source_url: str,
        project_id: str | None = None,
        name: str | None = None,
    ) -> Project:
        project = self.projects.load(project_id) if project_id else None
        if project:
            self._checkpoint(project).update(PipelineStage.INGEST, StageStatus.RUNNING)
        try:
            result = self.ingestor.ingest_file(path, source_url=source_url)
            project = project or self.projects.create((name or result.article.source.title)[:120])
            return self._persist(project, result)
        except Exception as exc:
            if project:
                self._checkpoint(project).update(PipelineStage.INGEST, StageStatus.FAILED, error=str(exc))
            raise

    def _checkpoint(self, project: Project) -> CheckpointStore:
        return CheckpointStore(self.projects.project_dir(project.id) / "checkpoint.json")

    def _persist(self, project: Project, result: IngestResult) -> Project:
        directory = self.projects.project_dir(project.id)
        checkpoint = self._checkpoint(project)
        checkpoint.update(PipelineStage.INGEST, StageStatus.RUNNING)
        atomic_write_model(directory / "source.json", result.article.source)
        atomic_write_text(directory / "article.md", result.article.markdown)
        atomic_write_model(directory / "images.json", result.article.images)
        digest = hashlib.sha256()
        digest.update(result.article.source.model_dump_json().encode("utf-8"))
        digest.update(result.article.markdown.encode("utf-8"))
        digest.update(result.article.images.model_dump_json().encode("utf-8"))
        checkpoint.update(
            PipelineStage.INGEST,
            StageStatus.COMPLETED,
            fingerprint=f"sha256:{digest.hexdigest()}",
            metadata={"extraction_method": result.article.source.extraction_method, "image_count": len(result.article.images.images)},
        )
        return project
