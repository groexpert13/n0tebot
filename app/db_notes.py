from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
import logging

from .supabase_client import get_supabase

log = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today_date_str(tz: timezone = timezone.utc) -> str:
    return datetime.now(tz).date().isoformat()


def resolve_user_id_by_tg(tg_user_id: int) -> Optional[str]:
    """Return app_users.id (uuid) by Telegram user id. None if unavailable.

    Does NOT create the user; creation is handled elsewhere (start handler upsert).
    """
    client = get_supabase()
    if client is None:
        return None
    try:
        res = (
            client.table("app_users")
            .select("id")
            .eq("tg_user_id", tg_user_id)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        if not rows:
            return None
        return rows[0].get("id")
    except Exception as e:
        log.warning("resolve_user_id_by_tg failed: %s", e)
        return None


def create_note(
    *,
    user_id: str,
    content: str,
    title: Optional[str] = None,
    d: Optional[str] = None,
    source: Optional[str] = None,
) -> bool:
    """Insert a note row. Returns True on success, False otherwise.

    Fields: { user_id, d (YYYY-MM-DD), title?, content, source }
    """
    client = get_supabase()
    if client is None:
        return False
    try:
        payload: Dict[str, Any] = {
            "user_id": user_id,
            "d": d or _today_date_str(),
            "content": content,
            "source": source or "web",
            "updated_at": _now_iso(),
        }
        if title:
            payload["title"] = title
        client.table("notes").insert(payload).execute()
        return True
    except Exception as e:
        log.warning("create_note failed: %s", e)
        return False
