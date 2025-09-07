from __future__ import annotations

import asyncio
from typing import Optional

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

from ..state import get_user_state
from ..texts import (
    PROCESSING,
    PROCESSED_DONE,
    NEXT_PROMPT,
    OPEN_BUTTON,
)
from ..config import settings
from .ai import process_text_message, process_voice_message, process_video_note


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

    # If privacy not accepted yet, re-prompt politely
    if not state.accepted_privacy:
        await message.answer(
            "Please accept the Privacy Notice first." if lang == "en" else (
                "Спочатку прийміть Політику конфіденційності." if lang == "uk" else "Сначала примите Политику конфиденциальности."
            )
        )
        return

    # Clean up previous messages
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

    # Show processing message
    processing_text = PROCESSING.get(lang, PROCESSING["en"])
    processing_msg = await message.answer(processing_text)

    # Process through AI and save to DB
    success = False
    try:
        if message_type == "text":
            success = await process_text_message(message)
        elif message_type == "voice":
            success = await process_voice_message(message)
        elif message_type == "video_note":
            success = await process_video_note(message)
    except Exception:
        success = False

    # Remove processing message
    try:
        await message.bot.delete_message(message.chat.id, processing_msg.message_id)
    except Exception:
        pass

    if success:
        # Show success message with webapp button
        done_text = PROCESSED_DONE.get(lang, PROCESSED_DONE["en"]) 
        sent = await message.answer(done_text, reply_markup=open_button_kb(lang))
        state.last_content_message_id = sent.message_id
        # Send separate next prompt below the button
        hint = await message.answer(NEXT_PROMPT.get(lang, NEXT_PROMPT["en"]))
        state.last_prompt_message_id = hint.message_id
    else:
        # Show error message
        error_text = {
            "en": "Failed to process your message. Please try again.",
            "uk": "Не вдалося обробити ваше повідомлення. Спробуйте ще раз.",
            "ru": "Не удалось обработать ваше сообщение. Попробуйте ещё раз."
        }
        await message.answer(error_text.get(lang, error_text["en"]))


@router.message(F.text & ~F.via_bot & ~F.text.regexp(r"^/"))
async def handle_text(message: Message) -> None:
    await _handle_common(message, "text")


@router.message(F.voice)
async def handle_voice(message: Message) -> None:
    await _handle_common(message, "voice")


@router.message(F.video_note)
async def handle_video_note(message: Message) -> None:
    await _handle_common(message, "video_note")
