from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Any

@dataclass(frozen=True)
class EditorIteration:
    iteration: int
    issues: tuple[str, ...]
    changed_scenes: tuple[str, ...]
    qa_status: str

class BoundedAutonomousEditor:
    """Bounded inspect/edit/validate/preview/QA loop; facts are never edited."""
    def __init__(self, max_revisions: int = 3):
        if not 1 <= max_revisions <= 3: raise ValueError("max_revisions must be 1..3")
        self.max_revisions = max_revisions

    def run(self, inspect: Callable[[], Any], identify: Callable[[Any], list[str]], edit: Callable[[list[str]], list[str]], validate: Callable[[], Any], preview: Callable[[], Any], qa: Callable[[], dict[str, Any]]) -> list[EditorIteration]:
        history: list[EditorIteration] = []
        for number in range(1, self.max_revisions + 1):
            issues = identify(inspect())
            if not issues: break
            changed = tuple(dict.fromkeys(edit(issues)))
            validation = validate()
            preview()
            report = qa()
            history.append(EditorIteration(number, tuple(issues), changed, str(report.get("status", validation))))
            if report.get("status") == "pass": break
        return history
