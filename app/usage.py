from __future__ import annotations

import math
from typing import Optional

from .supabase_client import get_supabase
from .logger import append_usage_row


async def log_usage(
    *,
    tg_user_id: int,
    kind: str,
    input_tokens: int,
    output_tokens: int,
    total_tokens: int,
    voice_seconds: float = 0.0,
    model: Optional[str] = None,
) -> None:
    """
    Persist usage to Supabase counters (best effort) and append row to db.md.
    """
    # Append to file log (awaitable)
    await append_usage_row(
        tg_user_id=tg_user_id,
        kind="voice" if kind == "voice" else "text",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        voice_seconds=voice_seconds,
        model=model,
    )

    # Update Supabase user counters (best-effort, ignore failures)
    client = get_supabase()
    if client is None:
        return

    try:
        # The supabase-py doesn't support atomic increments directly; perform select+update (ideally via RPC in prod).
        # Here we'll do a simple stored procedure alternative: fetch current and update.
        res = (
            client.table("app_users").select("text_tokens_used_total, audio_minutes_total, text_generations_total, audio_generations_total").eq("tg_user_id", tg_user_id).limit(1).execute()
        )
        row = (res.data or [{}])[0]
        text_tokens = int(row.get("text_tokens_used_total") or 0)
        audio_minutes = int(row.get("audio_minutes_total") or 0)
        text_gens = int(row.get("text_generations_total") or 0)
        audio_gens = int(row.get("audio_generations_total") or 0)

        if total_tokens:
            text_tokens += int(total_tokens)
            text_gens += 1
        if voice_seconds:
            audio_minutes += int(math.ceil(voice_seconds / 60.0))
            audio_gens += 1

        client.table("app_users").update({
            "text_tokens_used_total": text_tokens,
            "text_generations_total": text_gens,
            "audio_minutes_total": audio_minutes,
            "audio_generations_total": audio_gens,
            "updated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        }).eq("tg_user_id", tg_user_id).execute()
    except Exception:
        # best effort only
        pass
