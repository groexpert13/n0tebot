import os
from typing import Optional, Callable, Awaitable

try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

from starlette.testclient import TestClient
from pathlib import Path
import sys


def main() -> int:
    # Ensure project root is on sys.path
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    # Import app and dispatcher
    from app.health import app, dp, bot  # type: ignore
    from app.config import settings  # type: ignore

    client = TestClient(app)

    # 1) Root health
    r = client.get("/")
    assert r.status_code == 200, f"Root health failed: {r.status_code} {r.text}"
    print("GET / ->", r.json())

    # 2) Webhook GET health
    r = client.get("/telegram/webhook")
    assert r.status_code == 200, f"Webhook GET failed: {r.status_code} {r.text}"
    print("GET /telegram/webhook ->", r.json())

    # 3) Webhook POST with minimal valid update
    payload = {
        "update_id": 1,
        "message": {
            "message_id": 1,
            "date": 0,
            "chat": {"id": 123, "type": "private"},
            "from": {"id": 123, "is_bot": False, "first_name": "Test"},
            "text": "ping",
        },
    }

    # Monkeypatch dispatcher feed_update to avoid real Telegram calls in handlers
    import types

    async def _dummy_feed_update(self, _bot, _update):
        return None

    original = dp.feed_update
    try:
        dp.feed_update = types.MethodType(_dummy_feed_update, dp)  # type: ignore
        headers = {}
        if settings.telegram_webhook_secret:
            headers["X-Telegram-Bot-Api-Secret-Token"] = settings.telegram_webhook_secret

        r = client.post("/telegram/webhook", json=payload, headers=headers)
        assert r.status_code == 200, f"Webhook POST failed: {r.status_code} {r.text}"
        print("POST /telegram/webhook ->", r.json())

        r = client.post("/telegram/webhook/", json=payload, headers=headers)
        assert r.status_code == 200, f"Webhook POST slash failed: {r.status_code} {r.text}"
        print("POST /telegram/webhook/ ->", r.json())
    finally:
        dp.feed_update = original  # type: ignore

    print("All webhook tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
