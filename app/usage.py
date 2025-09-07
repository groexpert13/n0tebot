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
        # Here we'll do a simple select + update. We also try to support optional columns if present.
        # 1) Fetch base counters that are guaranteed to exist in current schema
        res = (
            client.table("app_users")
            .select("text_tokens_used_total, text_generations_total, audio_minutes_total, audio_generations_total")
            .eq("tg_user_id", tg_user_id)
            .limit(1)
            .execute()
        )
        row = (res.data or [{}])[0]

        # Existing counters (base)
        text_tokens_sum = int(row.get("text_tokens_used_total") or 0)
        audio_seconds_sum = int(row.get("audio_minutes_total") or 0)  # stores SECONDS (despite the name)
        text_gens = int(row.get("text_generations_total") or 0)
        audio_gens = int(row.get("audio_generations_total") or 0)

        # 2) Try to fetch optional split token counters (if columns exist)
        text_input_sum = 0
        text_output_sum = 0
        opt_cols_present = False
        try:
            opt_res = (
                client.table("app_users")
                .select("text_input_tokens_total, text_output_tokens_total")
                .eq("tg_user_id", tg_user_id)
                .limit(1)
                .execute()
            )
            opt_row = (opt_res.data or [{}])[0]
            text_input_sum = int(opt_row.get("text_input_tokens_total") or 0)
            text_output_sum = int(opt_row.get("text_output_tokens_total") or 0)
            opt_cols_present = ("text_input_tokens_total" in opt_row) or ("text_output_tokens_total" in opt_row)
        except Exception:
            # Columns not present yet — silently ignore
            opt_cols_present = False

        # Normalize usage values
        in_toks = int(input_tokens or 0)
        out_toks = int(output_tokens or 0)
        tot_toks = int(total_tokens or 0)
        # If total is missing but parts are present, recompute
        if tot_toks == 0 and (in_toks or out_toks):
            tot_toks = in_toks + out_toks

        # Update counters depending on kind
        update_fields = {
            "updated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        }

        if kind == "text":
            # Count tokens only for TEXT messages
            if in_toks:
                text_input_sum += in_toks
            if out_toks:
                text_output_sum += out_toks
            if tot_toks:
                text_tokens_sum += tot_toks
            text_gens += 1

            update_fields.update({
                "text_tokens_used_total": text_tokens_sum,
                "text_generations_total": text_gens,
            })
            # Update optional split columns only if they exist in the row (prevents errors on older schemas)
            if opt_cols_present:
                update_fields["text_input_tokens_total"] = text_input_sum
                update_fields["text_output_tokens_total"] = text_output_sum

        elif kind == "voice":
            # Count SECONDS for audio/video-notes; do NOT add tokens here
            sec = int(max(0, math.floor(float(voice_seconds or 0))))
            if sec > 0:
                audio_seconds_sum += sec
                audio_gens += 1
            update_fields.update({
                "audio_minutes_total": audio_seconds_sum,  # stores SECONDS
                "audio_generations_total": audio_gens,
            })
        else:
            # Unknown kind: be conservative and do nothing but update timestamp
            pass

        client.table("app_users").update(update_fields).eq("tg_user_id", tg_user_id).execute()
    except Exception:
        # best effort only
        pass
