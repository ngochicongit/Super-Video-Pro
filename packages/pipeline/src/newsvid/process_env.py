from __future__ import annotations

import os
from pathlib import Path


def subprocess_environment(executable: str | None = None) -> dict[str, str]:
    """Return a UTF-8 child environment, treating Electron as its embedded Node when selected."""
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    if executable and Path(executable).stem.casefold() == "electron":
        env["ELECTRON_RUN_AS_NODE"] = "1"
    return env
