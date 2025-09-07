from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
)

from ..state import get_user_state
from ..texts import (
    choose_language_prompt,
    LANG_BUTTONS,
    PRIVACY_MESSAGE,
    PRIVACY_ACCEPT_BUTTON,
    PRIVACY_ALERT,
    PRO_MESSAGE,
    OPEN_BUTTON,
    NEXT_PROMPT,
)
from ..config import settings
from ..commands_setup import set_chat_commands
from ..db_users import upsert_visit_from_tg_user, set_user_language, set_privacy_accepted


router = Router(name=__name__)


def language_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text=LANG_BUTTONS["en"], callback_data="lang:en"),
            InlineKeyboardButton(text=LANG_BUTTONS["uk"], callback_data="lang:uk"),
            InlineKeyboardButton(text=LANG_BUTTONS["ru"], callback_data="lang:ru"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def accept_privacy_keyboard(lang: str) -> InlineKeyboardMarkup:
    text = PRIVACY_ACCEPT_BUTTON.get(lang, PRIVACY_ACCEPT_BUTTON["en"])
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=text, callback_data="privacy:accept")]]
    )


def open_button_kb(lang: str) -> InlineKeyboardMarkup:
    text = OPEN_BUTTON.get(lang, OPEN_BUTTON["en"])
    url = settings.webapp_url or "https://n0tes-black.vercel.app/"
    # Всегда используем WebApp-кнопку
    btn = InlineKeyboardButton(text=text, web_app=WebAppInfo(url=url))
    return InlineKeyboardMarkup(inline_keyboard=[[btn]])


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else message.chat.id
    state = get_user_state(user_id)
    state.accepted_privacy = False
    state.lang = None
    state.last_content_message_id = None
    state.last_prompt_message_id = None
    # Persist or update visit in DB
    if message.from_user:
        try:
            upsert_visit_from_tg_user(message.from_user)
        except Exception:
            pass
    await message.answer(choose_language_prompt(), reply_markup=language_keyboard())


@router.callback_query(F.data.startswith("lang:"))
async def on_language_chosen(cb: CallbackQuery) -> None:
    code = cb.data.split(":", 1)[1]
    if code not in ("en", "uk", "ru"):
        code = "en"
    user_id = cb.from_user.id
    state = get_user_state(user_id)
    state.lang = code
    state.accepted_privacy = False

    privacy_url = settings.privacy_url or "https://example.com/privacy"
    text = PRIVACY_MESSAGE.get(code, PRIVACY_MESSAGE["en"]).format(url=privacy_url)

    # Persist language choice
    try:
        set_user_language(user_id, code)
    except Exception:
        pass

    if cb.message:
        await cb.message.edit_text(text, reply_markup=accept_privacy_keyboard(code))
    await cb.answer()


@router.callback_query(F.data == "privacy:accept")
async def on_privacy_accept(cb: CallbackQuery) -> None:
    user_id = cb.from_user.id
    state = get_user_state(user_id)
    lang = state.lang or "en"
    state.accepted_privacy = True

    # Show alert with the note about data safety
    await cb.answer(PRIVACY_ALERT.get(lang, PRIVACY_ALERT["en"]), show_alert=True)

    # Persist privacy acceptance
    try:
        set_privacy_accepted(user_id)
    except Exception:
        pass

    # Заменяем текст на блок Pro/trial + кнопку (без подсказки)
    pro_text = PRO_MESSAGE.get(lang, PRO_MESSAGE["en"]) 
    if cb.message:
        await cb.message.edit_text(pro_text, reply_markup=open_button_kb(lang))
        state.last_content_message_id = cb.message.message_id
    # Отправляем отдельной строкой подсказку ниже
    hint = await cb.message.answer(NEXT_PROMPT.get(lang, NEXT_PROMPT["en"]))
    state.last_prompt_message_id = hint.message_id

    # Поставим локализованные команды для этого чата
    try:
        await set_chat_commands(cb.bot, cb.message.chat.id, lang)
    except Exception:
        pass
