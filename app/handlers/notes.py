from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from typing import Optional, List, Dict, Any

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

from ..state import get_user_state
from ..texts import (
    PROCESSING,
    PROCESSING_EMOJI,
    PROCESSED_DONE,
    NEXT_PROMPT,
    OPEN_BUTTON,
)
from ..config import settings
from ..openai_client import generate_text, transcribe_audio
from ..system_prompt import load_system_prompt
from ..db_users import upsert_visit_from_tg_user, get_privacy_accepted
from ..db_notes import resolve_user_id_by_tg, create_note
from ..usage import log_usage
from .ai import _forward_meta, _strip_trailing_json_block


router = Router(name=__name__)


def open_button_kb(lang: str) -> InlineKeyboardMarkup:
    text = OPEN_BUTTON.get(lang, OPEN_BUTTON["en"])
    url = settings.webapp_url or "https://n0tes-black.vercel.app/"
    # Prefer WebApp button; fall back to URL if not supported by client
    button = InlineKeyboardButton(text=text, web_app=WebAppInfo(url=url))
    return InlineKeyboardMarkup(inline_keyboard=[[button]])


async def _handle_common(message: Message, message_type: str = "text") -> None:
    user_id = message.from_user.id if message.from_user else message.chat.id
    state = get_user_state(user_id)
    lang = state.lang or "en"

    # If privacy not accepted in memory, hydrate from DB to avoid false negatives after restarts
    if not state.accepted_privacy:
        try:
            if get_privacy_accepted(user_id):
                state.accepted_privacy = True
        except Exception:
            pass
    # Still not accepted — re-prompt politely
    if not state.accepted_privacy:
        await message.answer(
            "Please accept the Privacy Notice first." if lang == "en" else (
                "Спочатку прийміть Політику конфіденційності." if lang == "uk" else "Сначала примите Политику конфиденциальности."
            )
        )
        return

    # Enqueue this message into the batch collector. The collector will
    # show a single set of processing messages and process all messages
    # arriving within a short time window as one note.
    await _enqueue_for_batch(message, message_type)


async def _enqueue_for_batch(message: Message, message_type: str) -> None:
    """Buffer messages per user and process them together after a short delay.

    - First message shows processing messages and schedules a task.
    - Subsequent messages reset the timer and are added to the batch.
    - After delay, all buffered messages are processed into a single note.
    """
    user_id = message.from_user.id if message.from_user else message.chat.id
    state = get_user_state(user_id)
    lang = state.lang or "en"

    # On the very first message of a batch: cleanup previous "done"+"hint"
    first_in_batch = (state.processing_msg_id is None and state.processing_emoji_msg_id is None)
    if first_in_batch:
        if state.last_content_message_id:
            try:
                await message.bot.delete_message(message.chat.id, state.last_content_message_id)
            except Exception:
                pass
            state.last_content_message_id = None
        if state.last_prompt_message_id:
            try:
                await message.bot.delete_message(message.chat.id, state.last_prompt_message_id)
            except Exception:
                pass
            state.last_prompt_message_id = None

        # Show a single pair of processing messages for the batch
        processing_text = PROCESSING.get(lang, PROCESSING["en"])
        processing_msg = await message.answer(processing_text)
        emoji_msg = await message.answer(PROCESSING_EMOJI)
        state.processing_msg_id = processing_msg.message_id
        state.processing_emoji_msg_id = emoji_msg.message_id

    # Add to buffer
    state.batch_items.append({"type": message_type, "message": message})

    # Reset/reschedule the task
    if state.batch_task is not None:
        try:
            state.batch_task.cancel()
        except Exception:
            pass
        state.batch_task = None

    # Short debounce window to collect multiple forwards (texts/voices/videos)
    state.batch_task = asyncio.create_task(_process_batch_after_delay(message, delay=0.9))


async def _process_batch_after_delay(message: Message, *, delay: float = 1.4) -> None:
    try:
        await asyncio.sleep(delay)
    except asyncio.CancelledError:
        return

    # Snapshot and clear the buffer
    user_id = message.from_user.id if message.from_user else message.chat.id
    state = get_user_state(user_id)
    items: List[Dict[str, Any]] = state.batch_items[:]
    state.batch_items.clear()
    state.batch_task = None

    if not items:
        # Nothing to do; clean processing messages if any
        try:
            if state.processing_msg_id:
                await message.bot.delete_message(message.chat.id, state.processing_msg_id)
            if state.processing_emoji_msg_id:
                await message.bot.delete_message(message.chat.id, state.processing_emoji_msg_id)
        except Exception:
            pass
        state.processing_msg_id = None
        state.processing_emoji_msg_id = None
        return

    await _process_batch_core(message, items)


async def _process_batch_core(message: Message, items: List[Dict[str, Any]]) -> None:
    """Process buffered messages into a single AI note and handle UX messages."""
    import logging
    log = logging.getLogger(__name__)

    user = message.from_user
    user_id = user.id if user else message.chat.id
    state = get_user_state(user_id)
    lang = state.lang or "en"

    # Prepare combined text: transcribe audios, include forward meta for each part
    parts: List[str] = []
    total_voice_seconds: float = 0.0

    try:
        # Concurrency with ordering preserved
        sem = asyncio.Semaphore(3)

        async def _process_one(idx: int, it: Dict[str, Any]):
            kind = it.get("type")
            msg: Message = it.get("message")
            prefix = _forward_meta(msg)
            added_seconds: float = 0.0
            text_out: str = ""

            async with sem:
                try:
                    bot = msg.bot
                    # Text-only
                    if kind == "text" and msg.text:
                        text_out = prefix + msg.text
                    # Voice note (OGG)
                    elif kind == "voice" and msg.voice:
                        file = await bot.get_file(msg.voice.file_id)
                        with tempfile.TemporaryDirectory() as tmpdir:
                            tmp_path = Path(tmpdir) / f"voice_{msg.voice.file_unique_id}.ogg"
                            await bot.download(file, destination=tmp_path)
                            t, _ = await transcribe_audio(file_path=str(tmp_path), language=(user.language_code if user else None))
                        if t:
                            text_out = prefix + t
                        added_seconds = float(msg.voice.duration or 0)
                    # Round video note (MP4/WEBM), extract audio track only
                    elif kind == "video_note" and msg.video_note:
                        file = await bot.get_file(msg.video_note.file_id)
                        with tempfile.TemporaryDirectory() as tmpdir:
                            tmp_path = Path(tmpdir) / f"video_note_{msg.video_note.file_unique_id}.mp4"
                            await bot.download(file, destination=tmp_path)
                            t, _ = await transcribe_audio(file_path=str(tmp_path), language=(user.language_code if user else None))
                        if t:
                            text_out = prefix + t
                        added_seconds = float(msg.video_note.duration or 0)
                    # Full video (extract audio only)
                    elif kind == "video" and msg.video:
                        file = await bot.get_file(msg.video.file_id)
                        with tempfile.TemporaryDirectory() as tmpdir:
                            tmp_path = Path(tmpdir) / f"video_{msg.video.file_unique_id}.mp4"
                            await bot.download(file, destination=tmp_path)
                            t, _ = await transcribe_audio(file_path=str(tmp_path), language=(user.language_code if user else None))
                        # Add caption if present
                        cap = (msg.caption or "").strip()
                        if t:
                            text_out = prefix + (cap + "\n\n" if cap else "") + t
                        elif cap:
                            text_out = prefix + cap
                        added_seconds = float(msg.video.duration or 0)
                    # Audio file (mp3/m4a/wav/ogg)
                    elif kind == "audio" and msg.audio:
                        file = await bot.get_file(msg.audio.file_id)
                        with tempfile.TemporaryDirectory() as tmpdir:
                            # try to keep extension
                            ext = Path(msg.audio.file_name or "audio").suffix or ".mp3"
                            tmp_path = Path(tmpdir) / f"audio_{msg.audio.file_unique_id}{ext}"
                            await bot.download(file, destination=tmp_path)
                            t, _ = await transcribe_audio(file_path=str(tmp_path), language=(user.language_code if user else None))
                        cap = (msg.caption or "").strip()
                        if t:
                            text_out = prefix + (cap + "\n\n" if cap else "") + t
                        elif cap:
                            text_out = prefix + cap
                        added_seconds = float(msg.audio.duration or 0)
                    # Document that is audio/video (by mime or filename); otherwise keep caption only
                    elif kind == "document" and msg.document:
                        mime = (msg.document.mime_type or "").lower()
                        name = (msg.document.file_name or "").lower()
                        is_media = (
                            mime.startswith("audio/") or mime.startswith("video/") or
                            any(name.endswith(ext) for ext in (".mp3", ".m4a", ".wav", ".ogg", ".flac", ".mp4", ".mkv", ".mov", ".webm"))
                        )
                        cap = (msg.caption or "").strip()
                        if is_media:
                            file = await bot.get_file(msg.document.file_id)
                            with tempfile.TemporaryDirectory() as tmpdir:
                                ext = Path(name).suffix or (".mp4" if "video" in mime else ".mp3")
                                tmp_path = Path(tmpdir) / f"doc_{msg.document.file_unique_id}{ext}"
                                await bot.download(file, destination=tmp_path)
                                t, _ = await transcribe_audio(file_path=str(tmp_path), language=(user.language_code if user else None))
                            # We cannot reliably get duration from document; 0 by default
                            if t:
                                text_out = prefix + (cap + "\n\n" if cap else "") + t
                            elif cap:
                                text_out = prefix + cap
                        else:
                            if cap:
                                text_out = prefix + cap
                    # Photo(s): keep only caption (no OCR)
                    elif kind == "photo" and getattr(msg, "photo", None):
                        cap = (msg.caption or "").strip()
                        if cap:
                            text_out = prefix + cap
                except Exception:
                    text_out = ""
                    added_seconds = 0.0

            return idx, text_out, added_seconds

        results = await asyncio.gather(*[_process_one(i, it) for i, it in enumerate(items)], return_exceptions=False)

        # Preserve original order
        for _, text_out, added_seconds in results:
            if text_out:
                parts.append(text_out)
            if added_seconds:
                total_voice_seconds += float(added_seconds)

        if not parts:
            raise RuntimeError("No content extracted from batch")

        # Build final prompt by joining parts in order
        prompt = ("\n\n---\n\n").join(parts)
        system_prompt: Optional[str] = load_system_prompt() or "Use context7 for reasoning and concise, helpful responses."

        # Persist visit and resolve user id
        if message.from_user:
            try:
                upsert_visit_from_tg_user(message.from_user)
            except Exception:
                pass
        uid = resolve_user_id_by_tg(user_id)
        if not uid:
            raise RuntimeError("User not found in app_users for saving note")

        # Call AI once for the combined content
        reply_text, usage = await generate_text(
            prompt=prompt,
            user_id=str(user_id),
            system_prompt=system_prompt,
        )

        # Log usage: text tokens, and voice seconds (if any)
        try:
            await log_usage(
                tg_user_id=user_id,
                kind="text",
                input_tokens=usage.get("input_tokens", 0),
                output_tokens=usage.get("output_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
                voice_seconds=0.0,
                model=None,
            )
            if total_voice_seconds > 0:
                await log_usage(
                    tg_user_id=user_id,
                    kind="voice",
                    input_tokens=0,
                    output_tokens=0,
                    total_tokens=0,
                    voice_seconds=total_voice_seconds,
                    model=None,
                )
        except Exception:
            pass

        # Sanitize and split into title/content
        full_text = _strip_trailing_json_block(reply_text)
        if not full_text or not full_text.strip():
            raise RuntimeError("AI response is empty")

        lines = full_text.strip().split("\n", 1)
        title = lines[0].strip() if lines else ""
        content = lines[1].strip() if len(lines) > 1 else ""
        if not content:
            content = title
            title = None

        # Save note with current time field
        from datetime import datetime, timezone
        current_time = datetime.now(timezone.utc).strftime("%H:%M")
        ok = create_note(user_id=uid, content=content, title=title, source="web", time=current_time)
        if not ok:
            raise RuntimeError("Failed to save note")

        # Remove processing messages
        try:
            if state.processing_msg_id:
                await message.bot.delete_message(message.chat.id, state.processing_msg_id)
            if state.processing_emoji_msg_id:
                await message.bot.delete_message(message.chat.id, state.processing_emoji_msg_id)
        except Exception:
            pass
        state.processing_msg_id = None
        state.processing_emoji_msg_id = None

        # Show success message with WebApp button and next prompt
        done_text = PROCESSED_DONE.get(lang, PROCESSED_DONE["en"]) 
        sent = await message.answer(done_text, reply_markup=open_button_kb(lang))
        state.last_content_message_id = sent.message_id
        hint = await message.answer(NEXT_PROMPT.get(lang, NEXT_PROMPT["en"]))
        state.last_prompt_message_id = hint.message_id

    except Exception as e:
        log.warning("batch processing failed: %s", e)
        # Remove processing messages
        try:
            if state.processing_msg_id:
                await message.bot.delete_message(message.chat.id, state.processing_msg_id)
            if state.processing_emoji_msg_id:
                await message.bot.delete_message(message.chat.id, state.processing_emoji_msg_id)
        except Exception:
            pass
        state.processing_msg_id = None
        state.processing_emoji_msg_id = None

        # Show generic error and menu
        error_text = {
            "en": "Failed to process your message. Please try again.",
            "uk": "Не вдалося обробити ваше повідомлення. Спробуйте ще раз.",
            "ru": "Не удалось обработать ваше сообщение. Попробуйте ещё раз.",
        }
        done_text = PROCESSED_DONE.get(lang, PROCESSED_DONE["en"]) 
        sent = await message.answer(done_text, reply_markup=open_button_kb(lang))
        state.last_content_message_id = sent.message_id
        err = await message.answer(f"⚠️ {error_text.get(lang, error_text['en'])}")
        state.last_prompt_message_id = err.message_id


@router.message(F.text & ~F.via_bot & ~F.text.regexp(r"^/"))
async def handle_text(message: Message) -> None:
    await _handle_common(message, "text")


@router.message(F.voice)
async def handle_voice(message: Message) -> None:
    await _handle_common(message, "voice")


@router.message(F.video_note)
async def handle_video_note(message: Message) -> None:
    await _handle_common(message, "video_note")


@router.message(F.video)
async def handle_video(message: Message) -> None:
    await _handle_common(message, "video")


@router.message(F.audio)
async def handle_audio(message: Message) -> None:
    await _handle_common(message, "audio")


@router.message(F.document)
async def handle_document(message: Message) -> None:
    await _handle_common(message, "document")


@router.message(F.photo)
async def handle_photo(message: Message) -> None:
    # Only caption is used (no OCR) — kept for order/context
    await _handle_common(message, "photo")
