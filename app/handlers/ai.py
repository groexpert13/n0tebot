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
            # Add link if username available
            link = f"https://t.me/{u.username}"
        else:
            link = None
        name = " ".join([x for x in [u.first_name, u.last_name] if x])
        if name:
            parts.append(name)
        parts.append(f"id={u.id}")
        
        # Format with link if available
        if link and u.username:
            return f"[Forwarded from [{', '.join(parts)}]({link})]\n\n"
        else:
            return "[Forwarded from " + ", ".join(parts) + "]\n\n"
    elif getattr(message, "forward_sender_name", None):
        parts.append(str(message.forward_sender_name))
        return "[Forwarded from " + ", ".join(parts) + "]\n\n"
    elif getattr(message, "forward_from_chat", None):
        ch = message.forward_from_chat
        chat_info = ch.title or ch.username or str(ch.id)
        if ch.username:
            link = f"https://t.me/{ch.username}"
            return f"[Forwarded from chat: [{chat_info}]({link})]\n\n"
        else:
            return f"[Forwarded from chat: {chat_info}]\n\n"
    return ""


def _strip_trailing_json_block(text: str) -> str:
    """Sanitize AI text so only plain text is stored in notes.

    Removes any fenced code blocks (```...```), including languages like
    ```json, ```sql, etc., anywhere in the text. This ensures we don't
    persist SQL/JSON/code snippets into the DB — only human-readable text.
    """
    import re

    if not text:
        return text

    # Remove all fenced code blocks of any language (greedy-safe, non-greedy body)
    # Examples removed: ```json ...```, ```sql ...```, ```python ...```, ``` ...```
    sanitized = re.sub(r"(?s)```.*?```", "\n", text)

    # Cleanup any leftover unmatched fences just in case
    sanitized = sanitized.replace("```", "")

    return sanitized.strip()


async def process_text_message(message: Message) -> bool:
    """Process text message through AI and save to DB. Returns True if successful."""
    import logging
    log = logging.getLogger(__name__)
    
    if not message.text:
        log.warning("process_text_message: empty message text")
        return False
    
    user = message.from_user
    user_id = user.id if user else message.chat.id
    log.info(f"process_text_message: starting for user {user_id}")

    try:
        # Load system prompt from repo (system-prompt.md), fallback to context7
        system_prompt: Optional[str] = load_system_prompt() or "Use context7 for reasoning and concise, helpful responses."
        log.info("process_text_message: system prompt loaded")

        forward_prefix = _forward_meta(message)
        if forward_prefix:
            log.info(f"process_text_message: forwarded message detected: {forward_prefix[:100]}...")

        log.info("process_text_message: calling OpenAI API")
        reply_text, usage = await generate_text(
            prompt=forward_prefix + message.text,
            user_id=str(user_id),
            system_prompt=system_prompt,
        )
        log.info(f"process_text_message: OpenAI response received, tokens: {usage.get('total_tokens', 0)}")
        log.info(f"process_text_message: AI response content length: {len(reply_text) if reply_text else 0}")
        log.info(f"process_text_message: AI response preview: {reply_text[:100] if reply_text else 'EMPTY'}")

        # Log usage best-effort
        log.info("process_text_message: logging usage")
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
        log.info("process_text_message: upserting user visit")
        if message.from_user:
            upsert_visit_from_tg_user(message.from_user)
        
        log.info("process_text_message: resolving user ID")
        uid = resolve_user_id_by_tg(user_id)
        if uid:
            log.info(f"process_text_message: creating note for user {uid}")
            # Save only the AI-processed content (without trailing JSON metadata)
            full_text = _strip_trailing_json_block(reply_text)
            if not full_text or not full_text.strip():
                log.warning("process_text_message: AI response is empty, not saving note")
                return False
            
            # Extract first line as title, rest as content
            lines = full_text.strip().split('\n', 1)
            title = lines[0].strip() if lines else ""
            content = lines[1].strip() if len(lines) > 1 else ""
            
            # If no content after title, use title as content and clear title
            if not content:
                content = title
                title = None
            
            # Get current time for the time field
            from datetime import datetime, timezone
            current_time = datetime.now(timezone.utc).strftime("%H:%M")
            
            log.info(f"process_text_message: saving title='{title[:50] if title else 'None'}...', content length={len(content)}, time={current_time}")
            success = create_note(user_id=uid, content=content, title=title, source="web", time=current_time)
            log.info(f"process_text_message: note creation {'succeeded' if success else 'failed'}")
            return success
        else:
            log.warning("process_text_message: could not resolve user ID")
            return False
    except Exception as e:
        log.error(f"process_text_message: exception occurred: {e}", exc_info=True)
        return False


async def process_voice_message(message: Message) -> bool:
    """Process voice message through AI and save to DB. Returns True if successful."""
    import logging
    log = logging.getLogger(__name__)
    
    voice = message.voice
    if not voice:
        log.warning("process_voice_message: no voice data")
        return False

    user = message.from_user
    user_id = user.id if user else message.chat.id
    log.info(f"process_voice_message: starting for user {user_id}")

    try:
        log.info("process_voice_message: downloading voice file")
        # Download OGG/OPUS to temp file
        bot = message.bot
        file = await bot.get_file(voice.file_id)

        # Prepare temp path
        suffix = ".oga"
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir) / f"voice_{voice.file_unique_id}{suffix}"
            await bot.download(file, destination=tmp_path)

            log.info("process_voice_message: transcribing audio")
            # Transcribe (Whisper accepts audio formats like ogg/oga)
            text, _ = await transcribe_audio(file_path=str(tmp_path), language=(user.language_code if user else None))

        if not text:
            log.warning("process_voice_message: transcription failed or empty")
            return False
        
        log.info(f"process_voice_message: transcription successful, length: {len(text)}")

        # Send recognized text to model including forward context
        forward_prefix = _forward_meta(message)
        if forward_prefix:
            log.info(f"process_voice_message: forwarded message detected: {forward_prefix[:100]}...")

        log.info("process_voice_message: calling OpenAI API")
        reply_text, usage = await generate_text(
            prompt=forward_prefix + text,
            user_id=str(user_id),
            system_prompt=load_system_prompt() or "Use context7 for reasoning and concise, helpful responses.",
        )
        log.info(f"process_voice_message: OpenAI response received, tokens: {usage.get('total_tokens', 0)}")

        # Log usage including voice duration (seconds from Telegram)
        log.info("process_voice_message: logging usage")
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
        log.info("process_voice_message: upserting user visit")
        if message.from_user:
            upsert_visit_from_tg_user(message.from_user)
        
        log.info("process_voice_message: resolving user ID")
        uid = resolve_user_id_by_tg(user_id)
        if uid:
            log.info(f"process_voice_message: creating note for user {uid}")
            # Save only the AI-processed content, without trailing JSON metadata
            full_text = _strip_trailing_json_block(reply_text)
            if not full_text or not full_text.strip():
                log.warning("process_voice_message: AI response is empty, not saving note")
                return False
            
            # Extract first line as title, rest as content
            lines = full_text.strip().split('\n', 1)
            title = lines[0].strip() if lines else ""
            content = lines[1].strip() if len(lines) > 1 else ""
            
            # If no content after title, use title as content and clear title
            if not content:
                content = title
                title = None
            
            # Get current time for the time field
            from datetime import datetime, timezone
            current_time = datetime.now(timezone.utc).strftime("%H:%M")
            
            log.info(f"process_voice_message: saving title='{title[:50] if title else 'None'}...', content length={len(content)}, time={current_time}")
            success = create_note(user_id=uid, content=content, title=title, source="web", time=current_time)
            log.info(f"process_voice_message: note creation {'succeeded' if success else 'failed'}")
            return success
        else:
            log.warning("process_voice_message: could not resolve user ID")
            return False
    except Exception as e:
        log.error(f"process_voice_message: exception occurred: {e}", exc_info=True)
        return False


async def process_video_note(message: Message) -> bool:
    """Process video note through AI and save to DB. Returns True if successful."""
    vn = message.video_note
    if not vn:
        return False

    user = message.from_user
    user_id = user.id if user else message.chat.id

    try:
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
            return False

        forward_prefix = _forward_meta(message)
        reply_text, usage = await generate_text(
            prompt=forward_prefix + text,
            user_id=str(user_id),
            system_prompt=load_system_prompt() or "Use context7 for reasoning and concise, helpful responses.",
        )

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
        if message.from_user:
            upsert_visit_from_tg_user(message.from_user)
        uid = resolve_user_id_by_tg(user_id)
        if uid:
            # Save only the AI-processed content, without trailing JSON metadata
            full_text = _strip_trailing_json_block(reply_text)
            if not full_text or not full_text.strip():
                log.warning("process_video_note: AI response is empty, not saving note")
                return False
            
            # Extract first line as title, rest as content
            lines = full_text.strip().split('\n', 1)
            title = lines[0].strip() if lines else ""
            content = lines[1].strip() if len(lines) > 1 else ""
            
            # If no content after title, use title as content and clear title
            if not content:
                content = title
                title = None
            
            # Get current time for the time field
            from datetime import datetime, timezone
            current_time = datetime.now(timezone.utc).strftime("%H:%M")
            
            log.info(f"process_video_note: saving title='{title[:50] if title else 'None'}...', content length={len(content)}, time={current_time}")
            success = create_note(user_id=uid, content=content, title=title, source="web", time=current_time)
            return success
        return False
    except Exception:
        return False
