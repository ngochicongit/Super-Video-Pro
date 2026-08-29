from __future__ import annotations

from .errors import SchemaValidationError
from .models import FactSet
from .script_models import NewsScript, SegmentType
from .storyboard_models import SceneType, Storyboard, StoryboardScene, StoryboardVideo
from .visual_router import RoutingContext, VisualRouter


class StoryboardBuilder:
    def __init__(self, router: VisualRouter | None = None) -> None:
        self.router = router or VisualRouter()

    def build(self, script: NewsScript, facts: FactSet, context: RoutingContext) -> Storyboard:
        valid_refs = {fact.id for fact in facts.facts}
        scenes: list[StoryboardScene] = []
        for index, segment in enumerate(script.segments, 1):
            unresolved = set(segment.fact_refs) - valid_refs
            if unresolved:
                raise SchemaValidationError(
                    f"Segment {segment.id} contains unresolved fact_refs: {', '.join(sorted(unresolved))}"
                )
            visual = self.router.route(segment, facts, context)
            semantic_type = (
                SceneType.HOOK if segment.type is SegmentType.HOOK
                else SceneType.OUTRO if segment.type is SegmentType.OUTRO
                else visual.type
            )
            scenes.append(StoryboardScene(
                id=f"scene_{index:03d}", script_segment_id=segment.id,
                type=semantic_type, narration=segment.narration,
                fact_refs=list(segment.fact_refs),
                duration_seconds=segment.estimated_duration_seconds,
                visual=visual,
            ))
        return Storyboard(
            video=StoryboardVideo(target_duration=script.target_duration_seconds,
                                  style=script.style),
            scenes=scenes,
        )
