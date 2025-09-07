from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Literal

# File-based append log into db.md as requested
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_DB_MD = _PROJECT_ROOT / "db.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def append_usage_row(
    *,
    tg_user_id: int,
    kind: Literal["text", "voice"],
    input_tokens: int,
    output_tokens: int,
    total_tokens: int,
    voice_seconds: float = 0.0,
    model: Optional[str] = None,
) -> None:
    """
    Append a row to db.md under a 'usage_log' section. If section is missing, create it.
    """
    ts = _now_iso()

    def _sync_append() -> None:
        # Ensure file exists
        if not _DB_MD.exists():
            _DB_MD.write_text("# Database Schema and Usage\n\n", encoding="utf-8")
        text = _DB_MD.read_text(encoding="utf-8")
        if "## usage_log" not in text:
            header = (
                "\n## usage_log\n\n"
                "| ts | tg_user_id | kind | voice_seconds | input_tokens | output_tokens | total_tokens | model |\n"
                "| -- | ---------- | ---- | ------------- | ------------ | ------------- | ------------ | ----- |\n"
            )
            text = text + header
            _DB_MD.write_text(text, encoding="utf-8")
        # Append row
        row = (
            f"| {ts} | {tg_user_id} | {kind} | {voice_seconds:.2f} | "
            f"{input_tokens} | {output_tokens} | {total_tokens} | {model or ''} |\n"
        )
        with _DB_MD.open("a", encoding="utf-8") as f:
            f.write(row)

    await asyncio.to_thread(_sync_append)
