from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from typing import Optional

from aiogram import Router, F
from aiogram.types import Message

from ..openai_client import generate_text, transcribe_audio
from ..usage import log_usage
from ..system_prompt import load_system_prompt
from ..db_users import upsert_visit_from_tg_user
from ..db_notes import resolve_user_id_by_tg, create_note

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


@router.message(F.text & ~F.text.startswith("/"))
async def handle_text_message(message: Message) -> None:
    if not message.text:
        return
    user = message.from_user
    user_id = user.id if user else message.chat.id

    # Load system prompt from repo (system-prompt.md), fallback to minimal one
    system_prompt: Optional[str] = load_system_prompt() or "Use context7 for reasoning and concise, helpful responses."

    forward_prefix = _forward_meta(message)

    reply_text, usage = await generate_text(
        prompt=forward_prefix + message.text,
        user_id=str(user_id),
        system_prompt=system_prompt,
    )

    await message.answer(reply_text or "")

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

    # Ensure user exists and persist note (best effort)
    try:
        if message.from_user:
            upsert_visit_from_tg_user(message.from_user)
        uid = resolve_user_id_by_tg(user_id)
        if uid:
            content = f"# Telegram text\n\n**Me:**\n{message.text}\n\n**AI:**\n{reply_text}"
            create_note(user_id=uid, content=content, source="tg-text")
    except Exception:
        pass


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
        await message.answer("Не удалось распознать речь. Попробуйте ещё раз.")
        return

    # Send recognized text to model including forward context
    forward_prefix = _forward_meta(message)
    reply_text, usage = await generate_text(
        prompt=forward_prefix + text,
        user_id=str(user_id),
        system_prompt=load_system_prompt() or "Use context7 for reasoning and concise, helpful responses.",
    )

    # Reply with transcript + answer
    await message.answer(f"🗣️ Распознано: {text}\n\n🤖 Ответ: {reply_text}")

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

    # Ensure user exists and persist note (best effort)
    try:
        if message.from_user:
            upsert_visit_from_tg_user(message.from_user)
        uid = resolve_user_id_by_tg(user_id)
        if uid:
            content = f"# Telegram voice\n\n**Transcript:**\n{text}\n\n**AI:**\n{reply_text}"
            create_note(user_id=uid, content=content, source="tg-voice")
    except Exception:
        pass


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
        await message.answer("Не удалось распознать видео-заметку. Попробуйте ещё раз.")
        return

    forward_prefix = _forward_meta(message)
    reply_text, usage = await generate_text(
        prompt=forward_prefix + text,
        user_id=str(user_id),
        system_prompt=load_system_prompt() or "Use context7 for reasoning and concise, helpful responses.",
    )

    await message.answer(f"🎥 Распознано (кружок): {text}\n\n🤖 Ответ: {reply_text}")

    await log_usage(
        tg_user_id=user_id,
        kind="voice",
        input_tokens=usage.get("input_tokens", 0),
        output_tokens=usage.get("output_tokens", 0),
        total_tokens=usage.get("total_tokens", 0),
        voice_seconds=float(vn.duration or 0),
        model=None,
    )

    # Ensure user exists and persist note (best effort)
    try:
        if message.from_user:
            upsert_visit_from_tg_user(message.from_user)
        uid = resolve_user_id_by_tg(user_id)
        if uid:
            content = f"# Telegram video note\n\n**Transcript:**\n{text}\n\n**AI:**\n{reply_text}"
            create_note(user_id=uid, content=content, source="tg-video_note")
    except Exception:
        pass
