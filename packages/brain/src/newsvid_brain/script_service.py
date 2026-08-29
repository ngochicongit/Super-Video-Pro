from __future__ import annotations

import re
from collections.abc import Callable

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
    validation_attempts = 3

    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider
        self.generation_mode = "model"

    def generate(self, facts: FactSet, *, target_duration: int = 60,
                 style: NewsStyle = NewsStyle.BREAKING_NEWS,
                 progress: Callable[[float, str, str], None] | None = None) -> NewsScript:
        if not 30 <= target_duration <= 90:
            raise ValueError("Target duration must be between 30 and 90 seconds")
        validation_error: SchemaValidationError | None = None
        for attempt in range(1, self.validation_attempts + 1):
            if progress:
                progress(0.12 + (attempt - 1) * 0.2, "script:generate",
                         f"Đang tạo kịch bản (lần {attempt}/{self.validation_attempts})")
            raw = self.provider.generate_structured(
                build_script_prompt(
                    facts, target_duration, style,
                    validation_error=str(validation_error) if validation_error else None,
                ),
                CandidateScript.model_json_schema(),
            )
            try:
                script = self._validate(raw, facts, target_duration=target_duration, style=style)
                self.generation_mode = "model"
                return script
            except SchemaValidationError as exc:
                validation_error = exc
        assert validation_error is not None
        if str(validation_error).startswith("Estimated narration duration"):
            if progress:
                progress(0.78, "script:fallback",
                         "Đang rút gọn kịch bản từ các dữ kiện đã xác thực")
            self.generation_mode = "deterministic-fallback"
            return self._fallback(facts, target_duration=target_duration, style=style)
        raise validation_error

    def _fallback(self, facts: FactSet, *, target_duration: int,
                  style: NewsStyle) -> NewsScript:
        target_words = round(target_duration * WORDS_PER_MINUTE / 60)
        minimum_words = round(target_words * 0.8)
        maximum_words = round(target_words * 1.2)
        ranked = sorted(enumerate(facts.facts), key=lambda item: (-item[1].importance, item[0]))
        states: dict[int, list[int]] = {0: []}
        for original_index, fact in ranked:
            count = _word_count(fact.claim)
            for total, selected in list(states.items())[::-1]:
                next_total = total + count
                if next_total <= maximum_words and next_total not in states:
                    states[next_total] = [*selected, original_index]
        viable = [total for total in states if minimum_words <= total <= maximum_words]
        units: list[tuple[str, str]] = []
        if viable:
            best = min(viable, key=lambda total: (abs(total - target_words), -total))
            for index in sorted(states[best]):
                fact = facts.facts[index]
                units.append((fact.id, fact.claim.strip()))
        else:
            remaining = target_words
            while remaining > 0:
                for _, fact in ranked:
                    words = fact.claim.split()
                    take = min(len(words), remaining)
                    if take:
                        units.append((fact.id, " ".join(words[:take])))
                        remaining -= take
                    if remaining == 0:
                        break
        while len(units) < 3:
            split_index = max(range(len(units)), key=lambda index: _word_count(units[index][1]))
            fact_id, text = units.pop(split_index)
            words = text.split()
            if len(words) < 2:
                units.insert(split_index, (fact_id, text))
                units.append((fact_id, text))
                continue
            midpoint = len(words) // 2
            units[split_index:split_index] = [
                (fact_id, " ".join(words[:midpoint])),
                (fact_id, " ".join(words[midpoint:])),
            ]
        groups: list[list[tuple[str, str]]] = []
        cursor = 0
        words_left = sum(_word_count(text) for _, text in units)
        for group_index in range(3):
            groups_left = 3 - group_index
            units_left = len(units) - cursor
            take_limit = units_left - (groups_left - 1)
            target = words_left / groups_left
            group: list[tuple[str, str]] = []
            group_words = 0
            while len(group) < take_limit:
                unit = units[cursor]
                group.append(unit)
                cursor += 1
                group_words += _word_count(unit[1])
                if group_words >= target:
                    break
            groups.append(group)
            words_left -= group_words
        kinds = [SegmentType.HOOK, SegmentType.BODY, SegmentType.OUTRO]
        segments: list[ScriptSegment] = []
        for index, (kind, group) in enumerate(zip(kinds, groups), 1):
            narration = " ".join(text for _, text in group).strip()
            refs = list(dict.fromkeys(fact_id for fact_id, _ in group))
            seconds = _word_count(narration) / (WORDS_PER_MINUTE / 60)
            segments.append(ScriptSegment(
                id=f"segment_{index:03d}", type=kind, narration=narration,
                fact_refs=refs, estimated_duration_seconds=round(seconds, 2),
            ))
        narration = " ".join(segment.narration for segment in segments)
        if not _looks_vietnamese(narration):
            raise SchemaValidationError("Facts are not recognizably Vietnamese for safe fallback")
        estimated = sum(segment.estimated_duration_seconds for segment in segments)
        return NewsScript(
            style=style, target_duration_seconds=target_duration,
            estimated_duration_seconds=round(estimated, 2),
            title=str(facts.source.title).strip()[:160], segments=segments,
        )

    def _validate(self, raw: dict, facts: FactSet, *, target_duration: int,
                  style: NewsStyle) -> NewsScript:
        raw_segments = raw.get("segments")
        if isinstance(raw_segments, list):
            for index, segment in enumerate(raw_segments, 1):
                if isinstance(segment, dict) and not segment.get("fact_refs"):
                    raise SchemaValidationError(f"Factual segment {index} must contain fact_refs")
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
