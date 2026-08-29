from __future__ import annotations

import re

from pydantic import ValidationError

from .errors import GroundingError, StructuredOutputError
from .models import CandidateFacts, Fact, FactSet, FactSource
from .prompts import build_fact_prompt
from .providers import LLMProvider


def _normalized(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def _unwrap_article_evidence(value: str) -> str:
    evidence = value.strip()
    wrapped = re.fullmatch(r"<article>\s*(.*?)\s*</article>", evidence,
                           flags=re.IGNORECASE | re.DOTALL)
    return wrapped.group(1).strip() if wrapped else evidence


class FactExtractor:
    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider

    def extract(self, article_markdown: str, source: FactSource) -> FactSet:
        article = article_markdown.strip()
        if not article:
            raise GroundingError("Article is empty")
        raw = self.provider.generate_structured(build_fact_prompt(article), CandidateFacts.model_json_schema())
        try:
            candidates = CandidateFacts.model_validate(raw)
        except ValidationError as exc:
            raise StructuredOutputError("LLM output failed the facts schema") from exc
        normalized_article = _normalized(article)
        facts: list[Fact] = []
        for index, candidate in enumerate(candidates.facts, 1):
            evidence = _unwrap_article_evidence(candidate.evidence)
            if _normalized(evidence) not in normalized_article:
                raise GroundingError(f"Evidence for candidate {index} is not present in article.md")
            payload = candidate.model_dump()
            payload["evidence"] = evidence
            facts.append(Fact(id=f"fact_{index:03d}", **payload))
        return FactSet(source=source, facts=facts)
