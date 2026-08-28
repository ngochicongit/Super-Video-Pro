from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup, Tag
from trafilatura import extract

from .errors import ArticleExtractionError
from .models import ArticleImage, ImageManifest, Source

NOISE_TAGS = ("script", "style", "noscript", "nav", "footer", "aside", "form", "iframe", "svg")


@dataclass(frozen=True)
class ExtractedArticle:
    source: Source
    markdown: str
    images: ImageManifest


def _meta(soup: BeautifulSoup, *keys: str) -> str | None:
    for key in keys:
        tag = soup.find("meta", attrs={"property": key}) or soup.find("meta", attrs={"name": key})
        value = tag.get("content") if isinstance(tag, Tag) else None
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _json_ld(soup: BeautifulSoup) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            raw = json.loads(tag.string or tag.get_text())
        except (TypeError, json.JSONDecodeError):
            continue
        candidates = raw if isinstance(raw, list) else raw.get("@graph", [raw]) if isinstance(raw, dict) else []
        values.extend(item for item in candidates if isinstance(item, dict))
    return values


def _ld_value(items: list[dict[str, Any]], key: str) -> Any:
    preferred = [item for item in items if str(item.get("@type", "")).lower() in {"article", "newsarticle", "reportagearticle"}]
    for item in [*preferred, *items]:
        if item.get(key):
            return item[key]
    return None


def _author(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, dict):
        return _author(value.get("name"))
    if isinstance(value, list):
        names = [name for item in value if (name := _author(item))]
        return ", ".join(names) or None
    return None


def _image_url(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return _image_url(value.get("url") or value.get("contentUrl"))
    if isinstance(value, list) and value:
        return _image_url(value[0])
    return None


def _absolute_http(value: str | None, base_url: str) -> str | None:
    if not value:
        return None
    resolved = urljoin(base_url, value.strip())
    return resolved if urlsplit(resolved).scheme in {"http", "https"} else None


def _int_attr(tag: Tag, name: str) -> int | None:
    raw = tag.get(name)
    if not isinstance(raw, str):
        return None
    match = re.search(r"\d+", raw)
    return int(match.group()) if match and int(match.group()) > 0 else None


def extract_images(soup: BeautifulSoup, url: str, hero: str | None) -> ImageManifest:
    collected: dict[str, ArticleImage] = {}
    for tag in soup.find_all("img"):
        raw = tag.get("src") or tag.get("data-src") or tag.get("data-original")
        source_url = _absolute_http(raw if isinstance(raw, str) else None, url)
        if not source_url or source_url.startswith(("data:", "blob:")):
            continue
        figure = tag.find_parent("figure")
        caption_tag = figure.find("figcaption") if isinstance(figure, Tag) else None
        caption = caption_tag.get_text(" ", strip=True) if isinstance(caption_tag, Tag) else None
        attribution_raw = tag.get("data-credit") or tag.get("data-attribution")
        attribution = attribution_raw.strip() if isinstance(attribution_raw, str) else caption
        alt_raw = tag.get("alt")
        item = ArticleImage(
            source_url=source_url,
            alt=alt_raw.strip() if isinstance(alt_raw, str) and alt_raw.strip() else None,
            caption=caption or None,
            attribution=attribution or None,
            width=_int_attr(tag, "width"),
            height=_int_attr(tag, "height"),
            is_hero=source_url == hero,
        )
        collected.setdefault(source_url, item)
    if hero and hero not in collected:
        collected[hero] = ArticleImage(source_url=hero, is_hero=True)
    return ImageManifest(source_url=url, images=list(collected.values()))


def dom_markdown(soup: BeautifulSoup, title: str) -> str:
    working = BeautifulSoup(str(soup), "html.parser")
    for tag in working.find_all(NOISE_TAGS):
        tag.decompose()
    root = working.find("article") or working.find("main") or working.body or working
    blocks: list[str] = [f"# {title}"]
    for tag in root.find_all(["h1", "h2", "h3", "p", "ul", "ol", "blockquote"], recursive=True):
        if tag.find_parent(["p", "ul", "ol", "blockquote"]):
            continue
        text = tag.get_text(" ", strip=True)
        if not text:
            continue
        if tag.name in {"h1", "h2", "h3"}:
            if text != title:
                blocks.append(f"{'#' * int(tag.name[1])} {text}")
        elif tag.name in {"ul", "ol"}:
            items = [item.get_text(" ", strip=True) for item in tag.find_all("li", recursive=False)]
            blocks.append("\n".join(f"- {item}" for item in items if item))
        elif tag.name == "blockquote":
            blocks.append(f"> {text}")
        elif len(text) >= 20:
            blocks.append(text)
    return "\n\n".join(blocks).strip() + "\n"


def extract_article(html: str, url: str, method: str) -> ExtractedArticle:
    soup = BeautifulSoup(html, "html.parser")
    ld = _json_ld(soup)
    h1 = soup.find("h1")
    title = str(_ld_value(ld, "headline") or _meta(soup, "og:title", "twitter:title") or (h1.get_text(" ", strip=True) if h1 else "") or (soup.title.get_text(" ", strip=True) if soup.title else "")).strip()
    if not title:
        raise ArticleExtractionError("Article title could not be extracted")
    hero = _absolute_http(_image_url(_ld_value(ld, "image")) or _meta(soup, "og:image", "twitter:image"), url)
    author = _author(_ld_value(ld, "author")) or _meta(soup, "author", "article:author")
    published = str(_ld_value(ld, "datePublished") or _meta(soup, "article:published_time", "date", "datePublished") or "").strip() or None
    html_tag = soup.find("html")
    language_raw = html_tag.get("lang") if isinstance(html_tag, Tag) else None
    language = (str(_ld_value(ld, "inLanguage") or _meta(soup, "content-language") or language_raw or "").strip() or None)
    markdown = extract(html, url=url, output_format="markdown", include_links=True, include_images=False, favor_precision=True, with_metadata=False) or ""
    if len(re.sub(r"\s+", " ", markdown).strip()) < 160:
        markdown = dom_markdown(soup, title)
    elif not markdown.lstrip().startswith("#"):
        markdown = f"# {title}\n\n{markdown.strip()}\n"
    if len(re.sub(r"[#*`>\s-]+", " ", markdown).strip()) < 120:
        raise ArticleExtractionError("Article body is too short after extraction")
    source = Source(
        url=url,
        domain=urlsplit(url).hostname or "unknown",
        title=title,
        author=author,
        published_at=published,
        language=language,
        hero_image=hero,
        retrieved_at=datetime.now(timezone.utc),
        extraction_method=method,
    )
    return ExtractedArticle(source=source, markdown=markdown, images=extract_images(soup, url, hero))
