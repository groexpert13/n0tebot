from __future__ import annotations

from typing import Optional
import logging

from .config import settings

try:
    from supabase import Client, create_client  # type: ignore
except Exception:  # pragma: no cover - package may not be installed yet
    Client = object  # type: ignore

    def create_client(*args, **kwargs):  # type: ignore
        raise RuntimeError(
            "Package 'supabase' is not installed. Add it to your environment."
        )


_supabase_client: Optional[Client] = None


def get_supabase() -> Optional[Client]:
    """Return a lazy-initialized Supabase client or None if env is incomplete.

    Note: As requested, we only initialize the client and do not perform
    any reads/writes until the table mapping is provided.
    """
    global _supabase_client

    if _supabase_client is not None:
        return _supabase_client

    if not settings.supabase_url or not settings.supabase_service_role_key:
        logging.getLogger(__name__).info(
            "Supabase env not fully configured; skipping client initialization"
        )
        return None

    try:
        _supabase_client = create_client(
            settings.supabase_url, settings.supabase_service_role_key
        )
        logging.getLogger(__name__).info("Supabase client initialized")
    except Exception as e:
        logging.getLogger(__name__).warning(
            "Failed to initialize Supabase client: %s", e
        )
        _supabase_client = None

    return _supabase_client

