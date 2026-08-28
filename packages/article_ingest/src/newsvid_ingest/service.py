from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .errors import ArticleExtractionError
from .extractor import ExtractedArticle, extract_article
from .fetchers import FetchedHtml, HtmlFetcher, LocalFileFetcher, PlaywrightFetcher, StaticFetcher


@dataclass(frozen=True)
class IngestResult:
    article: ExtractedArticle
    raw_html: str


class ArticleIngestor:
    def __init__(self, static_fetcher: HtmlFetcher | None = None, browser_fetcher: HtmlFetcher | None = None) -> None:
        self.static_fetcher = static_fetcher or StaticFetcher()
        self.browser_fetcher = browser_fetcher or PlaywrightFetcher()

    def ingest_url(self, url: str, *, browser_fallback: bool = True) -> IngestResult:
        static_error: ArticleExtractionError | None = None
        try:
            fetched = self.static_fetcher.fetch(url)
            return IngestResult(extract_article(fetched.html, fetched.final_url, fetched.method), fetched.html)
        except ArticleExtractionError as exc:
            static_error = exc
        if not browser_fallback:
            raise static_error
        try:
            fetched = self.browser_fetcher.fetch(url)
            return IngestResult(extract_article(fetched.html, fetched.final_url, fetched.method), fetched.html)
        except ArticleExtractionError as browser_error:
            raise ArticleExtractionError(f"Static extraction failed ({static_error}); browser fallback failed ({browser_error})") from browser_error

    def ingest_file(self, path: Path, *, source_url: str = "https://fixture.invalid/article") -> IngestResult:
        fetched: FetchedHtml = LocalFileFetcher().fetch(path, source_url)
        return IngestResult(extract_article(fetched.html, fetched.final_url, fetched.method), fetched.html)
