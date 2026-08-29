from __future__ import annotations

import re
from dataclasses import dataclass

from .models import FactSet
from .script_models import ScriptSegment, SegmentType
from .storyboard_models import SceneType, SourceType, VisualPlan, VisualProvenance

VISUAL_ROUTER_VERSION = "visual-router-v1"

_NUMBER = re.compile(r"(?<!\w)(?:\d[\d.,]*(?:\s*(?:%|phần trăm|triệu|tỷ|nghìn|đồng))?|(?:một|hai|ba|bốn|năm|sáu|bảy|tám|chín|mười)\s+(?:phần trăm|triệu|tỷ|nghìn|đồng|người|kỹ sư|năm|tháng|ngày))", re.I)
_CHRONOLOGY = re.compile(r"\b(?:năm\s+\d{4}|tháng\s+\d+|ngày\s+\d+|trước đó|sau đó|tiếp theo|đầu tiên|cuối cùng|giai đoạn|trong ba năm)\b", re.I)
_COMPARISON = re.compile(r"\b(?:so với|cao hơn|thấp hơn|tăng|giảm|gấp|chênh lệch)\b", re.I)
_LOCATION = re.compile(r"\b(?:tại|ở|thành phố|tỉnh|quốc gia|khu vực|địa phương|bản đồ)\b", re.I)
_REAL = re.compile(r"\b(?:ông|bà|tổng thống|thủ tướng|giám đốc|ceo|hội nghị|sự kiện|lễ|cuộc họp|ra mắt|công bố)\b", re.I)
_SOFTWARE = re.compile(r"\b(?:website|trang web|ứng dụng|phần mềm|nền tảng|giao diện|hệ thống trực tuyến)\b", re.I)
_QUOTE = re.compile(r"(?:“[^”]+”|\"[^\"]+\"|cho biết|phát biểu rằng)", re.I)
_LIST = re.compile(r"\b(?:bao gồm|gồm có|các điểm|các tính năng|thứ nhất|thứ hai)\b", re.I)


@dataclass(frozen=True)
class RoutingContext:
    article_image_url: str | None
    article_url: str


class VisualRouter:
    """Deterministic, fact-aware visual selection; never defaults real subjects to AI."""

    def route(self, segment: ScriptSegment, facts: FactSet, context: RoutingContext) -> VisualPlan:
        fact_by_id = {fact.id: fact for fact in facts.facts}
        grounded_text = " ".join(
            f"{fact_by_id[ref].claim} {fact_by_id[ref].evidence}"
            for ref in segment.fact_refs if ref in fact_by_id
        )
        text = f"{segment.narration} {grounded_text}"
        if segment.type is SegmentType.HOOK:
            return self._graphic(SceneType.KINETIC_TEXT, "frame-kinetic-type",
                                 {"headline": segment.narration})
        if segment.type is SegmentType.OUTRO:
            return self._graphic(SceneType.OUTRO, "frame-logo-outro",
                                 {"closing_text": segment.narration})
        if _REAL.search(text):
            if context.article_image_url:
                return VisualPlan(
                    type=SceneType.ARTICLE_IMAGE, template="article-source-image",
                    provenance=VisualProvenance(source_type=SourceType.ARTICLE,
                                                source_url=context.article_image_url),
                    data={"caption": segment.narration},
                )
            return VisualPlan(
                type=SceneType.SCREENSHOT, template="article-source-screenshot",
                provenance=VisualProvenance(source_type=SourceType.SCREENSHOT,
                                            source_url=context.article_url),
                data={"reason": "real subject/event without an extracted source image"},
            )
        if _QUOTE.search(text):
            return self._graphic(SceneType.QUOTE, "news-quote", {"quote": segment.narration})
        if _CHRONOLOGY.search(text):
            return self._graphic(SceneType.TIMELINE, "news-timeline", {"text": segment.narration})
        numbers = list(dict.fromkeys(match.strip() for match in _NUMBER.findall(text)))
        if _COMPARISON.search(text) and len(numbers) >= 2:
            return self._graphic(SceneType.COMPARISON, "comparison-split",
                                 {"values": numbers[:4], "text": segment.narration})
        if len(numbers) >= 2:
            return self._graphic(SceneType.CHART, "frame-data-chart-nyt",
                                 {"values": numbers[:12], "title": segment.narration})
        if len(numbers) == 1:
            return self._graphic(SceneType.STAT_HERO, "frame-pentagram-stat",
                                 {"value": numbers[0], "label": segment.narration})
        if _LOCATION.search(text):
            return self._graphic(SceneType.MAP, "news-location-map", {"text": segment.narration})
        if _SOFTWARE.search(text):
            return VisualPlan(
                type=SceneType.SCREENSHOT, template="source-screenshot",
                provenance=VisualProvenance(source_type=SourceType.SCREENSHOT,
                                            source_url=context.article_url),
                data={"subject": segment.narration},
            )
        if _LIST.search(text):
            return self._graphic(SceneType.FEATURE_LIST, "feature-list",
                                 {"text": segment.narration})
        return VisualPlan(
            type=SceneType.AI_ILLUSTRATION, template="news-ai-illustration",
            provenance=VisualProvenance(source_type=SourceType.GENERATED,
                                        generator="comfyui", workflow="news-image"),
            prompt=f"Minh họa báo chí trung tính, không thêm chữ hoặc dữ kiện: {segment.narration}",
            data={"reason": "abstract concept without suitable source media"},
        )

    @staticmethod
    def _graphic(scene_type: SceneType, template: str, data: dict[str, object]) -> VisualPlan:
        return VisualPlan(type=scene_type, template=template,
                          provenance=VisualProvenance(source_type=SourceType.GRAPHIC), data=data)
