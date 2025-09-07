from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

from ..state import get_user_state
from ..texts import (
    CMD_NOTE_REPLY,
    CMD_BILLING_REPLY,
    PRIVACY_MESSAGE,
    OPEN_BUTTON,
    NEXT_PROMPT,
    CMD_DELETE_REPLY,
)
from ..config import settings


router = Router(name=__name__)


def open_button_kb(lang: str) -> InlineKeyboardMarkup:
    text = OPEN_BUTTON.get(lang, OPEN_BUTTON["en"])
    url = settings.webapp_url or "https://n0tes-black.vercel.app/"
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=text, web_app=WebAppInfo(url=url))]])


@router.message(Command("n0te"))
async def cmd_n0te(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else message.chat.id
    state = get_user_state(user_id)
    lang = state.lang or "en"

    # Clean last bot content and prompt messages
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

    text = CMD_NOTE_REPLY.get(lang, CMD_NOTE_REPLY["en"]) 
    sent = await message.answer(text, reply_markup=open_button_kb(lang))
    state.last_content_message_id = sent.message_id
    hint = await message.answer(NEXT_PROMPT.get(lang, NEXT_PROMPT["en"]))
    state.last_prompt_message_id = hint.message_id


@router.message(Command("privacy"))
async def cmd_privacy(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else message.chat.id
    state = get_user_state(user_id)
    lang = state.lang or "en"
    url = settings.privacy_url or "https://example.com/privacy"
    await message.answer(PRIVACY_MESSAGE.get(lang, PRIVACY_MESSAGE["en"]).format(url=url))


@router.message(Command("billing"))
async def cmd_billing(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else message.chat.id
    state = get_user_state(user_id)
    lang = state.lang or "en"
    await message.answer(CMD_BILLING_REPLY.get(lang, CMD_BILLING_REPLY["en"]))


@router.message(Command("delete"))
async def cmd_delete(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else message.chat.id
    state = get_user_state(user_id)
    lang = state.lang or "en"
    await message.answer(CMD_DELETE_REPLY.get(lang, CMD_DELETE_REPLY["en"]))
