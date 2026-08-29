from __future__ import annotations

from pathlib import Path
from types import ModuleType
import sys

import pytest

from newsvid.checkpoint import CheckpointStore
from newsvid.ingestion import IngestionCoordinator
from newsvid.persistence import load_model
from newsvid.project import ProjectManager
from newsvid.schemas import PipelineStage, StageStatus
from newsvid_ingest.errors import ArticleExtractionError
from newsvid_ingest.extractor import extract_article
from newsvid_ingest.fetchers import FetchedHtml, PlaywrightFetcher
from newsvid_ingest.models import ImageManifest, Source
from newsvid_ingest.security import assert_public_http_url
from newsvid_ingest.service import ArticleIngestor

ROOT = Path(__file__).parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "article_vi.html"
FIXTURE_URL = "https://news.example.vn/cong-nghe/trung-tam-ai"


class FakeFetcher:
    def __init__(self, result: FetchedHtml | Exception) -> None:
        self.result = result
        self.calls = 0

    def fetch(self, _url: str) -> FetchedHtml:
        self.calls += 1
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def fixture_html() -> str:
    return FIXTURE.read_text(encoding="utf-8")


def test_local_vietnamese_fixture_extracts_markdown_metadata_and_images() -> None:
    result = ArticleIngestor().ingest_file(FIXTURE, source_url=FIXTURE_URL).article
    assert result.source.title == "Việt Nam ra mắt trung tâm AI mới"
    assert result.source.author == "Nguyễn Minh"
    assert result.source.published_at == "2026-08-20T08:30:00+07:00"
    assert result.source.language == "vi"
    assert str(result.source.hero_image) == "https://news.example.vn/media/hero-ai.jpg"
    assert "Mục tiêu trong ba năm" in result.markdown
    assert "alert('untrusted" not in result.markdown
    assert "Nội dung chân trang" not in result.markdown
    assert len(result.images.images) == 2
    assert result.images.images[0].is_hero
    assert result.images.images[0].attribution == "Ảnh: Tòa soạn"


def test_static_failure_uses_browser_fallback() -> None:
    static = FakeFetcher(ArticleExtractionError("static blocked"))
    browser = FakeFetcher(FetchedHtml(fixture_html(), FIXTURE_URL, "playwright"))
    result = ArticleIngestor(static, browser).ingest_url(FIXTURE_URL)
    assert result.article.source.extraction_method == "playwright"
    assert static.calls == browser.calls == 1


def test_browser_fallback_can_be_disabled() -> None:
    static = FakeFetcher(ArticleExtractionError("static blocked"))
    browser = FakeFetcher(FetchedHtml(fixture_html(), FIXTURE_URL, "playwright"))
    with pytest.raises(ArticleExtractionError, match="static blocked"):
        ArticleIngestor(static, browser).ingest_url(FIXTURE_URL, browser_fallback=False)
    assert browser.calls == 0


def test_playwright_adapter_captures_rendered_html_and_blocks_private_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    routed: dict[str, int] = {"continued": 0, "aborted": 0}

    class Route:
        def __init__(self, url: str) -> None:
            self.request = type("Request", (), {"url": url})()
        def continue_(self) -> None:
            routed["continued"] += 1
        def abort(self) -> None:
            routed["aborted"] += 1

    class Page:
        url = FIXTURE_URL
        def route(self, _pattern: str, handler: object) -> None:
            self.handler = handler
        def goto(self, _url: str, **_kwargs: object) -> object:
            self.handler(Route("http://127.0.0.1/private"))
            self.handler(Route("https://cdn.example.org/public.css"))
            return type("Response", (), {"ok": True, "status": 200})()
        def wait_for_timeout(self, _milliseconds: int) -> None: pass
        def content(self) -> str: return fixture_html()

    class Context:
        def new_page(self) -> Page: return Page()
        def close(self) -> None: pass

    class Browser:
        def new_context(self, **_kwargs: object) -> Context: return Context()
        def close(self) -> None: pass

    class Chromium:
        def launch(self, **_kwargs: object) -> Browser: return Browser()

    class Runtime:
        chromium = Chromium()
        def __enter__(self) -> "Runtime": return self
        def __exit__(self, *_args: object) -> None: pass

    package = ModuleType("playwright")
    sync_api = ModuleType("playwright.sync_api")
    sync_api.sync_playwright = lambda: Runtime()  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "playwright", package)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", sync_api)
    monkeypatch.setattr("newsvid_ingest.fetchers.assert_public_http_url", lambda value: value if value == FIXTURE_URL else assert_public_http_url(value, resolve_dns=False))
    fetched = PlaywrightFetcher().fetch(FIXTURE_URL)
    assert fetched.method == "playwright"
    assert "trung tâm AI" in fetched.html
    assert routed == {"continued": 1, "aborted": 1}


def test_ingestion_writes_three_valid_outputs_and_completes_checkpoint(tmp_path: Path) -> None:
    projects = ProjectManager(tmp_path / "projects")
    coordinator = IngestionCoordinator(projects)
    project = coordinator.ingest_file(FIXTURE, source_url=FIXTURE_URL)
    directory = projects.project_dir(project.id)
    source = load_model(directory / "source.json", Source)
    images = load_model(directory / "images.json", ImageManifest)
    article = (directory / "article.md").read_text(encoding="utf-8")
    checkpoint = CheckpointStore(directory / "checkpoint.json").load()
    assert source.title in article
    assert images.images
    assert checkpoint.stages[PipelineStage.INGEST].status is StageStatus.COMPLETED
    assert checkpoint.stages[PipelineStage.INGEST].fingerprint.startswith("sha256:")
    assert not (directory / "facts.json").exists()


def test_dom_heuristic_handles_page_when_trafilatura_has_too_little_content(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("newsvid_ingest.extractor.extract", lambda *_args, **_kwargs: None)
    result = extract_article(fixture_html(), FIXTURE_URL, "static")
    assert result.markdown.startswith("# Việt Nam ra mắt trung tâm AI mới")
    assert "Hạ tầng và hợp tác" in result.markdown


@pytest.mark.parametrize("url", [
    "http://127.0.0.1/article",
    "http://10.1.2.3/article",
    "http://169.254.169.254/latest/meta-data",
    "file:///C:/secret.txt",
    "https://user:secret@example.com/article",
])
def test_url_guard_rejects_local_and_non_http_targets(url: str) -> None:
    with pytest.raises(ArticleExtractionError):
        assert_public_http_url(url, resolve_dns=False)
