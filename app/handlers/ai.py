from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from typing import Optional

from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

from ..openai_client import generate_text, transcribe_audio
from ..usage import log_usage
from ..system_prompt import load_system_prompt
from ..db_users import upsert_visit_from_tg_user
from ..db_notes import resolve_user_id_by_tg, create_note
from ..state import get_user_state
from ..texts import PROCESSED_DONE, ERROR_TRY_AGAIN, OPEN_BUTTON
from ..config import settings

router = Router(name=__name__)


def _forward_meta(message: Message) -> str:
    """Build a short prefix describing original sender if message was forwarded."""
    parts = []
    if getattr(message, "forward_from", None):
        u = message.forward_from
        if u.username:
            parts.append(f"@{u.username}")
        name = " ".join([x for x in [u.first_name, u.last_name] if x])
        if name:
            parts.append(name)
        parts.append(f"id={u.id}")
    elif getattr(message, "forward_sender_name", None):
        parts.append(str(message.forward_sender_name))
    elif getattr(message, "forward_from_chat", None):
        ch = message.forward_from_chat
        parts.append(f"chat:{ch.title or ch.username or ch.id}")
    if parts:
        return "[Forwarded from " + ", ".join(parts) + "]\n\n"
    return ""


def _open_button_kb(lang: str) -> InlineKeyboardMarkup:
    text = OPEN_BUTTON.get(lang, OPEN_BUTTON["en"])
    url = settings.webapp_url or "https://n0tes-black.vercel.app/"
    btn = InlineKeyboardButton(text=text, web_app=WebAppInfo(url=url))
    return InlineKeyboardMarkup(inline_keyboard=[[btn]])


@router.message(F.text & ~F.text.startswith("/"))
async def handle_text_message(message: Message) -> None:
    if not message.text:
        return
    user = message.from_user
    user_id = user.id if user else message.chat.id

    # Load system prompt from repo (system-prompt.md), fallback per request
    system_prompt: Optional[str] = load_system_prompt() or "Use context7 for reasoning and concise, helpful responses."

    forward_prefix = _forward_meta(message)

    ai_ok = False
    reply_text = ""
    usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    try:
        reply_text, usage = await generate_text(
            prompt=forward_prefix + message.text,
            user_id=str(user_id),
            system_prompt=system_prompt,
        )
        ai_ok = bool(reply_text)
    except Exception:
        ai_ok = False

    # Log usage best-effort
    await log_usage(
        tg_user_id=user_id,
        kind="text",
        input_tokens=usage.get("input_tokens", 0),
        output_tokens=usage.get("output_tokens", 0),
        total_tokens=usage.get("total_tokens", 0),
        voice_seconds=0.0,
        model=None,
    )

    # Ensure user exists and persist note
    saved = False
    try:
        if message.from_user:
            upsert_visit_from_tg_user(message.from_user)
        uid = resolve_user_id_by_tg(user_id)
        if uid and ai_ok:
            content = f"# Telegram text\n\n**Me:**\n{message.text}\n\n**AI:**\n{reply_text}"
            saved = bool(create_note(user_id=uid, content=content, source="tg-text"))
    except Exception:
        saved = False

    # Localized outcome message (no AI content in chat)
    lang = get_user_state(user_id).lang or "en"
    if ai_ok and saved:
        await message.answer(PROCESSED_DONE.get(lang, PROCESSED_DONE["en"]), reply_markup=_open_button_kb(lang))
    else:
        await message.answer(ERROR_TRY_AGAIN.get(lang, ERROR_TRY_AGAIN["en"]))


@router.message(F.voice)
async def handle_voice_message(message: Message) -> None:
    voice = message.voice
    if not voice:
        return

    user = message.from_user
    user_id = user.id if user else message.chat.id

    # Download OGG/OPUS to temp file
    bot = message.bot
    file = await bot.get_file(voice.file_id)

    # Prepare temp path
    suffix = ".oga"
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir) / f"voice_{voice.file_unique_id}{suffix}"
        await bot.download(file, destination=tmp_path)

        # Transcribe (Whisper accepts audio formats like ogg/oga)
        text, _ = await transcribe_audio(file_path=str(tmp_path), language=(user.language_code if user else None))

    if not text:
        lang = get_user_state(user_id).lang or "en"
        await message.answer(ERROR_TRY_AGAIN.get(lang, ERROR_TRY_AGAIN["en"]))
        return

    # Send recognized text to model including forward context
    forward_prefix = _forward_meta(message)
    ai_ok = False
    reply_text = ""
    usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    try:
        reply_text, usage = await generate_text(
            prompt=forward_prefix + text,
            user_id=str(user_id),
            system_prompt=load_system_prompt() or "Use context7 for reasoning and concise, helpful responses.",
        )
        ai_ok = bool(reply_text)
    except Exception:
        ai_ok = False

    # Log usage including voice duration (seconds from Telegram)
    await log_usage(
        tg_user_id=user_id,
        kind="voice",
        input_tokens=usage.get("input_tokens", 0),
        output_tokens=usage.get("output_tokens", 0),
        total_tokens=usage.get("total_tokens", 0),
        voice_seconds=float(voice.duration or 0),
        model=None,
    )

    # Ensure user exists and persist note
    saved = False
    try:
        if message.from_user:
            upsert_visit_from_tg_user(message.from_user)
        uid = resolve_user_id_by_tg(user_id)
        if uid and ai_ok:
            content = f"# Telegram voice\n\n**Transcript:**\n{text}\n\n**AI:**\n{reply_text}"
            saved = bool(create_note(user_id=uid, content=content, source="tg-voice"))
    except Exception:
        saved = False

    lang = get_user_state(user_id).lang or "en"
    if ai_ok and saved:
        await message.answer(PROCESSED_DONE.get(lang, PROCESSED_DONE["en"]), reply_markup=_open_button_kb(lang))
    else:
        await message.answer(ERROR_TRY_AGAIN.get(lang, ERROR_TRY_AGAIN["en"]))


@router.message(F.video_note)
async def handle_video_note(message: Message) -> None:
    vn = message.video_note
    if not vn:
        return

    user = message.from_user
    user_id = user.id if user else message.chat.id

    bot = message.bot
    file = await bot.get_file(vn.file_id)

    # Download to temp (mp4/webm)
    with tempfile.TemporaryDirectory() as tmpdir:
        # Preserve extension best-effort
        ext = ".mp4"
        tmp_path = Path(tmpdir) / f"video_note_{vn.file_unique_id}{ext}"
        await bot.download(file, destination=tmp_path)

        # Whisper supports mp4/webm; pass the video file directly
        text, _ = await transcribe_audio(file_path=str(tmp_path), language=(user.language_code if user else None))

    if not text:
        lang = get_user_state(user_id).lang or "en"
        await message.answer(ERROR_TRY_AGAIN.get(lang, ERROR_TRY_AGAIN["en"]))
        return

    forward_prefix = _forward_meta(message)
    ai_ok = False
    reply_text = ""
    usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    try:
        reply_text, usage = await generate_text(
            prompt=forward_prefix + text,
            user_id=str(user_id),
            system_prompt=load_system_prompt() or "Use context7 for reasoning and concise, helpful responses.",
        )
        ai_ok = bool(reply_text)
    except Exception:
        ai_ok = False

    await log_usage(
        tg_user_id=user_id,
        kind="voice",
        input_tokens=usage.get("input_tokens", 0),
        output_tokens=usage.get("output_tokens", 0),
        total_tokens=usage.get("total_tokens", 0),
        voice_seconds=float(vn.duration or 0),
        model=None,
    )

    # Ensure user exists and persist note
    saved = False
    try:
        if message.from_user:
            upsert_visit_from_tg_user(message.from_user)
        uid = resolve_user_id_by_tg(user_id)
        if uid and ai_ok:
            content = f"# Telegram video note\n\n**Transcript:**\n{text}\n\n**AI:**\n{reply_text}"
            saved = bool(create_note(user_id=uid, content=content, source="tg-video_note"))
    except Exception:
        saved = False

    lang = get_user_state(user_id).lang or "en"
    if ai_ok and saved:
        await message.answer(PROCESSED_DONE.get(lang, PROCESSED_DONE["en"]), reply_markup=_open_button_kb(lang))
    else:
        await message.answer(ERROR_TRY_AGAIN.get(lang, ERROR_TRY_AGAIN["en"]))
