from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from urllib.parse import urljoin

import httpx

from .errors import ArticleExtractionError
from .security import assert_public_http_url

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36 SuperVideoPro/1"


@dataclass(frozen=True)
class FetchedHtml:
    html: str
    final_url: str
    method: str


class HtmlFetcher(Protocol):
    def fetch(self, url: str) -> FetchedHtml: ...


class StaticFetcher:
    def __init__(self, timeout_seconds: float = 20, max_bytes: int = 5_000_000, max_redirects: int = 5) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_bytes = max_bytes
        self.max_redirects = max_redirects

    def fetch(self, url: str) -> FetchedHtml:
        current = assert_public_http_url(url)
        with httpx.Client(timeout=self.timeout_seconds, follow_redirects=False, headers={"User-Agent": USER_AGENT}) as client:
            for _ in range(self.max_redirects + 1):
                response = client.get(current, headers={"Accept": "text/html,application/xhtml+xml"})
                if response.is_redirect:
                    location = response.headers.get("location")
                    if not location:
                        raise ArticleExtractionError("Article redirect did not include a destination")
                    current = assert_public_http_url(urljoin(current, location))
                    continue
                try:
                    response.raise_for_status()
                except httpx.HTTPError as exc:
                    raise ArticleExtractionError(f"Static article fetch failed: HTTP {response.status_code}") from exc
                content_type = response.headers.get("content-type", "").lower()
                if "html" not in content_type and "xhtml" not in content_type:
                    raise ArticleExtractionError(f"Article URL returned unsupported content type: {content_type or 'unknown'}")
                if len(response.content) > self.max_bytes:
                    raise ArticleExtractionError(f"Article HTML exceeds {self.max_bytes} bytes")
                return FetchedHtml(response.text, str(response.url), "static")
        raise ArticleExtractionError(f"Article exceeded {self.max_redirects} redirects")


class PlaywrightFetcher:
    def __init__(self, timeout_ms: int = 30_000) -> None:
        self.timeout_ms = timeout_ms

    def fetch(self, url: str) -> FetchedHtml:
        assert_public_http_url(url)
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise ArticleExtractionError("Playwright is unavailable; install the Phase 1 dependencies") from exc
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context(java_script_enabled=True, service_workers="block", accept_downloads=False)
                page = context.new_page()

                def protect(route: object) -> None:
                    request_url = route.request.url  # type: ignore[attr-defined]
                    try:
                        assert_public_http_url(request_url)
                        route.continue_()  # type: ignore[attr-defined]
                    except ArticleExtractionError:
                        route.abort()  # type: ignore[attr-defined]

                page.route("**/*", protect)
                response = page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_ms)
                if response is None or not response.ok:
                    status = response.status if response else "no response"
                    raise ArticleExtractionError(f"Browser article fetch failed: {status}")
                page.wait_for_timeout(750)
                final_url = assert_public_http_url(page.url)
                html = page.content()
                context.close()
                browser.close()
                return FetchedHtml(html, final_url, "playwright")
        except ArticleExtractionError:
            raise
        except Exception as exc:
            raise ArticleExtractionError(f"Playwright fallback failed: {exc}") from exc


class LocalFileFetcher:
    def fetch(self, path: Path, source_url: str = "https://fixture.invalid/article") -> FetchedHtml:
        if path.suffix.lower() not in {".html", ".htm"}:
            raise ArticleExtractionError("Local fixture must be an HTML file")
        try:
            html = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise ArticleExtractionError(f"Could not read local HTML fixture: {path}") from exc
        return FetchedHtml(html, source_url, "local-fixture")
