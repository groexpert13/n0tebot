from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
import logging

from aiogram.types import User as TgUser

from .supabase_client import get_supabase


log = logging.getLogger(__name__)


def _now() -> str:
    # ISO 8601 string with timezone (PostgREST accepts str and converts)
    return datetime.now(timezone.utc).isoformat()


def _fetch_user_by_tg_id(tg_user_id: int) -> Optional[Dict[str, Any]]:
    client = get_supabase()
    if client is None:
        return None
    try:
        res = (
            client.table("app_users")
            .select("id, visits_count")
            .eq("tg_user_id", tg_user_id)
            .execute()
        )
        data = res.data or []
        return data[0] if data else None
    except Exception as e:
        log.warning("fetch user failed: %s", e)
        return None


def get_privacy_accepted(tg_user_id: int) -> Optional[bool]:
    """Return True/False if user row exists, or None if not found/unavailable."""
    client = get_supabase()
    if client is None:
        return None
    try:
        res = (
            client.table("app_users")
            .select("privacy_accepted")
            .eq("tg_user_id", tg_user_id)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        if not rows:
            return None
        return bool(rows[0].get("privacy_accepted"))
    except Exception as e:
        log.warning("get privacy_accepted failed: %s", e)
        return None


def upsert_visit_from_tg_user(user: TgUser, platform: str = "telegram-bot") -> None:
    """Create user row if missing, or update last visit and increment visits_count."""
    client = get_supabase()
    if client is None:
        return

    base_fields: Dict[str, Any] = {
        "tg_user_id": user.id,
        "tg_username": user.username,
        "tg_first_name": user.first_name,
        "tg_last_name": user.last_name,
        "tg_language_code": getattr(user, "language_code", None),
        "tg_is_premium": getattr(user, "is_premium", None),
        "last_platform": platform,
        "last_visit_at": _now(),
        "updated_at": _now(),
    }

    existing = _fetch_user_by_tg_id(user.id)
    try:
        if existing:
            visits = existing.get("visits_count") or 0
            fields = {**base_fields, "visits_count": int(visits) + 1}
            client.table("app_users").update(fields).eq("tg_user_id", user.id).execute()
        else:
            fields = {
                **base_fields,
                "timezone": "UTC",
                "visits_count": 1,
                "subscription_status": "none",
            }
            client.table("app_users").insert(fields).execute()
    except Exception as e:
        log.warning("upsert visit failed: %s", e)


def upsert_visit_from_webapp_user(user: Dict[str, Any], platform: str = "webapp") -> None:
    """Create/update an app_users row based on Telegram WebApp `initData.user` dict.

    Expects keys: id, username?, first_name?, last_name?, language_code?, is_premium?, photo_url?
    """
    client = get_supabase()
    if client is None:
        return

    tg_user_id = int(user.get("id"))
    base_fields: Dict[str, Any] = {
        "tg_user_id": tg_user_id,
        "tg_username": user.get("username"),
        "tg_first_name": user.get("first_name"),
        "tg_last_name": user.get("last_name"),
        "tg_language_code": user.get("language_code"),
        "tg_is_premium": user.get("is_premium"),
        "tg_photo_url": user.get("photo_url"),
        "last_platform": platform,
        "last_visit_at": _now(),
        "updated_at": _now(),
    }

    existing = _fetch_user_by_tg_id(tg_user_id)
    try:
        if existing:
            visits = existing.get("visits_count") or 0
            fields = {**base_fields, "visits_count": int(visits) + 1}
            client.table("app_users").update(fields).eq("tg_user_id", tg_user_id).execute()
        else:
            fields = {
                **base_fields,
                "timezone": "UTC",
                "visits_count": 1,
                "subscription_status": "none",
            }
            client.table("app_users").insert(fields).execute()
    except Exception as e:
        log.warning("upsert webapp visit failed: %s", e)


def resolve_user_basic_info(tg_user_id: int) -> Optional[Dict[str, Any]]:
    """Return {id, web_language_code, timezone, privacy_accepted} by Telegram user id.

    Returns None if user is not found or client unavailable.
    """
    client = get_supabase()
    if client is None:
        return None
    try:
        res = (
            client.table("app_users")
            .select("id, web_language_code, timezone, privacy_accepted")
            .eq("tg_user_id", tg_user_id)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        if not rows:
            return None
        row = rows[0]
        return {
            "id": row.get("id"),
            "web_language_code": row.get("web_language_code"),
            "timezone": row.get("timezone"),
            "privacy_accepted": bool(row.get("privacy_accepted")),
        }
    except Exception as e:
        log.warning("resolve basic info failed: %s", e)
        return None


def set_user_language(tg_user_id: int, lang_code: str) -> None:
    client = get_supabase()
    if client is None:
        return
    try:
        # Make sure row exists
        if not _fetch_user_by_tg_id(tg_user_id):
            # If missing, create a minimal row
            client.table("app_users").insert({
                "tg_user_id": tg_user_id,
                "timezone": "UTC",
                "visits_count": 0,
                "subscription_status": "none",
                "created_at": _now(),
                "updated_at": _now(),
            }).execute()

        client.table("app_users").update({
            "web_language_code": lang_code,
            "language_confirmed_at": _now(),
            "updated_at": _now(),
        }).eq("tg_user_id", tg_user_id).execute()
    except Exception as e:
        log.warning("set language failed: %s", e)


def set_privacy_accepted(tg_user_id: int) -> None:
    client = get_supabase()
    if client is None:
        return
    try:
        # Ensure row exists
        if not _fetch_user_by_tg_id(tg_user_id):
            client.table("app_users").insert({
                "tg_user_id": tg_user_id,
                "timezone": "UTC",
                "visits_count": 0,
                "subscription_status": "none",
                "created_at": _now(),
                "updated_at": _now(),
            }).execute()

        client.table("app_users").update({
            "privacy_accepted": True,
            "privacy_accepted_at": _now(),
            "updated_at": _now(),
        }).eq("tg_user_id", tg_user_id).execute()
    except Exception as e:
        log.warning("set privacy failed: %s", e)
