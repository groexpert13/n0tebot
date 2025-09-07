from __future__ import annotations

import hmac
import hashlib
import json
import time
from typing import Dict, List, Tuple, Optional
from urllib.parse import parse_qsl

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from .config import settings
from .db_users import (
    upsert_visit_from_webapp_user,
    resolve_user_basic_info,
)

app = FastAPI()


@app.get("/")
async def root():
    return {"status": "ok"}


class ResolveUserRequest(BaseModel):
    init_data: str


def _build_data_check_string(pairs: List[Tuple[str, str]]) -> str:
    # Exclude 'hash' and sort by key
    clean = [(k, v) for k, v in pairs if k != "hash"]
    clean.sort(key=lambda kv: kv[0])
    return "\n".join([f"{k}={v}" for k, v in clean])


def _compute_login_widget_hex(bot_token: str, data: str) -> str:
    # Legacy Login Widget: secret = SHA256(bot_token), HMAC_SHA256(data, secret)
    secret = hashlib.sha256(bot_token.encode("utf-8")).digest()
    mac = hmac.new(secret, data.encode("utf-8"), hashlib.sha256).hexdigest()
    return mac


def _compute_webapp_hex(bot_token: str, data: str) -> str:
    # WebApp: secret = HMAC_SHA256("WebAppData", bot_token), HMAC_SHA256(data, secret)
    secret = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    mac = hmac.new(secret, data.encode("utf-8"), hashlib.sha256).hexdigest()
    return mac


def _verify_init_data(init_data: str, bot_token: str) -> Dict[str, str]:
    # Parse into pairs (URL-decoded)
    pairs = parse_qsl(init_data, keep_blank_values=True)
    data: Dict[str, str] = {k: v for k, v in pairs}
    provided = (data.get("hash") or "").lower()
    if not provided:
        raise HTTPException(status_code=400, detail="Missing hash in init_data")

    dcs = _build_data_check_string(pairs)
    # Accept either WebApp or LoginWidget scheme (to be robust)
    calc_webapp = _compute_webapp_hex(bot_token, dcs)
    calc_login = _compute_login_widget_hex(bot_token, dcs)
    if not (hmac.compare_digest(provided, calc_webapp) or hmac.compare_digest(provided, calc_login)):
        raise HTTPException(status_code=401, detail="Invalid init_data signature")

    # Optional freshness check
    try:
        auth_date = int(data.get("auth_date", "0"))
    except ValueError:
        auth_date = 0
    if auth_date and (time.time() - auth_date > 86400):  # 24h window
        raise HTTPException(status_code=401, detail="init_data expired")

    return data


@app.post("/resolve-user")
async def resolve_user(req: ResolveUserRequest):
    if not settings.bot_token:
        raise HTTPException(status_code=500, detail="BOT_TOKEN missing")

    data = _verify_init_data(req.init_data, settings.bot_token)

    user_raw = data.get("user")
    if not user_raw:
        raise HTTPException(status_code=400, detail="init_data missing user")
    try:
        user_obj = json.loads(user_raw)
    except Exception:
        raise HTTPException(status_code=400, detail="user field is not valid JSON")

    # Upsert visit and fetch basic info
    try:
        upsert_visit_from_webapp_user(user_obj, platform="webapp")
    except Exception:
        # proceed to read if row already exists
        pass

    info = resolve_user_basic_info(int(user_obj.get("id")))
    if not info:
        raise HTTPException(status_code=404, detail="user not found")

    return info


@app.get("/resolve-user")
async def resolve_user_get(init_data: str = Query(..., description="initData from Telegram WebApp")):
    # Convenience GET variant
    return await resolve_user(ResolveUserRequest(init_data=init_data))
