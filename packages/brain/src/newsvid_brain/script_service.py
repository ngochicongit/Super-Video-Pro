from __future__ import annotations

import re

from pydantic import ValidationError

from .errors import SchemaValidationError
from .models import FactSet
from .providers import LLMProvider
from .script_models import CandidateScript, NewsScript, NewsStyle, ScriptSegment, SegmentType
from .script_prompts import WORDS_PER_MINUTE, build_script_prompt

_VIETNAMESE_MARKS = re.compile(r"[ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]", re.I)
_VIETNAMESE_WORDS = {"và", "của", "là", "được", "trong", "với", "cho", "tại", "những", "một", "này", "theo"}


def _word_count(value: str) -> int:
    return len(re.findall(r"\S+", value))


def _looks_vietnamese(value: str) -> bool:
    if _VIETNAMESE_MARKS.search(value):
        return True
    words = set(re.findall(r"\b\w+\b", value.casefold()))
    return len(words & _VIETNAMESE_WORDS) >= 3


class ScriptGenerator:
    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider

    def generate(self, facts: FactSet, *, target_duration: int = 60,
                 style: NewsStyle = NewsStyle.BREAKING_NEWS) -> NewsScript:
        if not 30 <= target_duration <= 90:
            raise ValueError("Target duration must be between 30 and 90 seconds")
        raw = self.provider.generate_structured(
            build_script_prompt(facts, target_duration, style), CandidateScript.model_json_schema()
        )
        try:
            candidate = CandidateScript.model_validate(raw)
        except ValidationError as exc:
            raise SchemaValidationError("LLM output failed the Vietnamese news script schema") from exc
        valid_refs = {fact.id for fact in facts.facts}
        segments: list[ScriptSegment] = []
        for index, segment in enumerate(candidate.segments, 1):
            refs = list(dict.fromkeys(segment.fact_refs))
            unresolved = set(refs) - valid_refs
            if unresolved:
                raise SchemaValidationError(
                    f"Segment {index} contains unresolved fact_refs: {', '.join(sorted(unresolved))}"
                )
            if not refs:
                raise SchemaValidationError(f"Factual segment {index} must contain fact_refs")
            seconds = _word_count(segment.narration) / (WORDS_PER_MINUTE / 60)
            segments.append(ScriptSegment(
                id=f"segment_{index:03d}", type=segment.type, narration=segment.narration.strip(),
                fact_refs=refs, estimated_duration_seconds=round(seconds, 2),
            ))
        narration = " ".join(segment.narration for segment in segments)
        if not _looks_vietnamese(narration):
            raise SchemaValidationError("Script narration is not recognizably Vietnamese")
        estimated = sum(segment.estimated_duration_seconds for segment in segments)
        tolerance = target_duration * 0.2
        if abs(estimated - target_duration) > tolerance:
            raise SchemaValidationError(
                f"Estimated narration duration {estimated:.1f}s is outside the 20% target window"
            )
        try:
            return NewsScript(style=style, target_duration_seconds=target_duration,
                              estimated_duration_seconds=round(estimated, 2),
                              title=candidate.title.strip(), segments=segments)
        except ValidationError as exc:
            raise SchemaValidationError("Generated script structure is invalid") from exc
