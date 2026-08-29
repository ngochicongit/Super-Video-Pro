from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ChangeKind(StrEnum):
    NARRATION = "narration"
    VISUAL = "visual"
    TEMPLATE = "template"
    TRANSITION = "transition"


@dataclass(frozen=True)
class InvalidationPlan:
    """Deterministic dependency plan for a storyboard edit."""

    scenes: tuple[str, ...] = ()
    regenerate_tts: bool = False
    regenerate_alignment: bool = False
    regenerate_captions: bool = False
    reassemble: bool = False


def plan_invalidation(kind: ChangeKind | str, scene_ids: list[str] | tuple[str, ...] = ()) -> InvalidationPlan:
    ids = tuple(dict.fromkeys(scene_ids))
    change = ChangeKind(kind)
    if change is ChangeKind.NARRATION:
        return InvalidationPlan(ids, True, True, True, True)
    if change is ChangeKind.VISUAL or change is ChangeKind.TEMPLATE:
        return InvalidationPlan(ids, False, False, False, True)
    return InvalidationPlan((), False, False, False, True)

