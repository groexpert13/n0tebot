from __future__ import annotations

import hmac
import hashlib
import json
import time
from typing import Dict, List, Tuple, Optional
from urllib.parse import parse_qsl

from fastapi import FastAPI, HTTPException, Query, Request, Header, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .config import settings
from .db_users import (
    upsert_visit_from_webapp_user,
    resolve_user_basic_info,
)
from .supabase_client import get_supabase
from .routes.billing import router as billing_router

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Update

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include billing routes
app.include_router(billing_router)

# Initialize aiogram Bot/Dispatcher for webhook mode
bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Attach routers similar to polling setup
try:
    from .handlers import start_router, misc_router, commands_router, notes_router

    dp.include_router(notes_router)
    dp.include_router(start_router)
    dp.include_router(misc_router)
    dp.include_router(commands_router)
except Exception:
    # If handlers are missing for any reason, continue with health endpoints only
    pass

# Optionally attach Supabase to workflow_data (used by handlers)
try:
    supabase = get_supabase()
    if supabase is not None:
        dp.workflow_data["supabase"] = supabase
except Exception:
    pass


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


@app.options("/resolve-user")
async def resolve_user_options():
    """Handle CORS preflight for resolve-user endpoint"""
    return JSONResponse(content={}, headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
        "Access-Control-Allow-Headers": "*"
    })

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


@app.post("/telegram/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: Optional[str] = Header(default=None),
    background_tasks: BackgroundTasks = None,
):
    # Optional verification via secret header if set
    if settings.telegram_webhook_secret:
        if not x_telegram_bot_api_secret_token or x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
            raise HTTPException(status_code=401, detail="Invalid webhook secret")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    try:
        update = Update.model_validate(payload)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid update payload")

    # Feed update to aiogram dispatcher in background to ACK immediately
    if background_tasks is not None:
        background_tasks.add_task(dp.feed_update, bot, update)
    else:
        # Fallback if BackgroundTasks is unavailable
        import asyncio
        asyncio.create_task(dp.feed_update(bot, update))
    return {"ok": True}


# Accept trailing slash just in case Telegram or proxies append it
@app.post("/telegram/webhook/")
async def telegram_webhook_slash(
    request: Request,
    x_telegram_bot_api_secret_token: Optional[str] = Header(default=None),
    background_tasks: BackgroundTasks = None,
):
    return await telegram_webhook(request, x_telegram_bot_api_secret_token, background_tasks)


# Convenience GET for quick health checks (doesn't process updates)
@app.get("/telegram/webhook")
async def telegram_webhook_get():
    return {"status": "ok"}
