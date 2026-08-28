from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class AdvancedWorkflow:
    name: str
    enabled: bool = False
    reason: str = "optional workflow is disabled"

SUPPORTED_ADVANCED = ("wan", "ltx", "animatediff")

def available_workflows(config: dict[str, Any] | None = None) -> list[AdvancedWorkflow]:
    config = config or {}
    return [AdvancedWorkflow(name, bool(config.get(name, False)), "ComfyUI video workflow not configured") for name in SUPPORTED_ADVANCED]

def advanced_visuals_enabled(config: dict[str, Any] | None = None) -> bool:
    return any(item.enabled for item in available_workflows(config))
