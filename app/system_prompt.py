from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Optional

# Cached loader for system-prompt.md in project root
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_PROMPT_PATH = _PROJECT_ROOT / "system-prompt.md"

_cached_text: Optional[str] = None
_cached_mtime: float = 0.0


def load_system_prompt() -> Optional[str]:
    global _cached_text, _cached_mtime
    try:
        st = _PROMPT_PATH.stat()
    except FileNotFoundError:
        return None

    if _cached_text is not None and abs(st.st_mtime - _cached_mtime) < 0.5:
        return _cached_text

    text = _PROMPT_PATH.read_text(encoding="utf-8")
    _cached_text = text.strip()
    _cached_mtime = st.st_mtime
    return _cached_text
