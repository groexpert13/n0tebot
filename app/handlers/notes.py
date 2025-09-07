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


router = Router(name=__name__)


def open_button_kb(lang: str) -> InlineKeyboardMarkup:
    text = OPEN_BUTTON.get(lang, OPEN_BUTTON["en"])
    url = settings.webapp_url or "https://n0tes-black.vercel.app/"
    # Prefer WebApp button; fall back to URL if not supported by client
    button = InlineKeyboardButton(text=text, web_app=WebAppInfo(url=url))
    return InlineKeyboardMarkup(inline_keyboard=[[button]])


async def _handle_common(message: Message) -> None:
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

    # Удалить предыдущие сообщения (контент и подсказка), чтобы чат оставался чистым
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

    # Processing placeholder (clock emoji)
    processing_text = PROCESSING.get(lang, PROCESSING["en"])
    processing_msg = await message.answer(processing_text)

    # Simulate processing
    await asyncio.sleep(1.0)

    # Remove processing message
    try:
        await message.bot.delete_message(message.chat.id, processing_msg.message_id)
    except Exception:
        pass

    # Compose final message with button (without the next prompt)
    done_text = PROCESSED_DONE.get(lang, PROCESSED_DONE["en"]) 
    sent = await message.answer(done_text, reply_markup=open_button_kb(lang))
    state.last_content_message_id = sent.message_id
    # Send separate next prompt below the button
    hint = await message.answer(NEXT_PROMPT.get(lang, NEXT_PROMPT["en"]))
    state.last_prompt_message_id = hint.message_id


@router.message(F.text & ~F.via_bot & ~F.text.regexp(r"^/"))
async def handle_text(message: Message) -> None:
    await _handle_common(message)


@router.message(F.voice | F.audio)
async def handle_audio(message: Message) -> None:
    await _handle_common(message)
