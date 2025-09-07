from __future__ import annotations

from typing import Dict, Literal

Lang = Literal["en", "uk", "ru"]


LANG_BUTTONS: Dict[str, str] = {
    "en": "English",
    "uk": "Українська",
    "ru": "Русский",
}


def choose_language_prompt() -> str:
    # As requested: ask in English
    return "Please choose your language:"


PRIVACY_MESSAGE: Dict[Lang, str] = {
    "en": (
        "Privacy Notice: {url}\n"
        "• Read and accept to continue"
    ),
    "uk": (
        "Політика конфіденційності: {url}\n"
        "• Прочитайте та прийміть, щоб продовжити"
    ),
    "ru": (
        "Политика конфиденциальности: {url}\n"
        "• Прочитайте и примите, чтобы продолжить"
    ),
}

PRIVACY_ACCEPT_BUTTON: Dict[Lang, str] = {
    "en": "I accept",
    "uk": "Приймаю",
    "ru": "Принимаю",
}

PRIVACY_ALERT: Dict[Lang, str] = {
    "en": (
        "• Your data isn’t shared with third parties.\n"
        "• AI is used only to process notes.\n"
        "• Avoid sharing sensitive personal data."
    ),
    "uk": (
        "• Ваші дані не передаються третім особам.\n"
        "• AI використовується лише для обробки нотаток.\n"
        "• Уникайте надсилання чутливих персональних даних."
    ),
    "ru": (
        "• Ваши данные не передаются третьим лицам.\n"
        "• ИИ используется только для обработки заметок.\n"
        "• Избегайте передачи чувствительных персональных данных."
    ),
}


PRO_MESSAGE: Dict[Lang, str] = {
    "en": (
        "Pro trial — 7 days\n"
        "• Send or forward audio/text to process\n"
        "• Private by default; avoid sensitive data"
    ),
    "uk": (
        "Pro-тріал — 7 днів\n"
        "• Надсилайте або пересилайте аудіо/текст на обробку\n"
        "• Приватність за замовчуванням; уникайте чутливих даних"
    ),
    "ru": (
        "Pro-триал — 7 дней\n"
        "• Отправляйте или пересылайте аудио/текст на обработку\n"
        "• По умолчанию приватно; избегайте чувствительных данных"
    ),
}


OPEN_BUTTON: Dict[Lang, str] = {
    "en": "Open n0te",
    "uk": "Відкрити n0te",
    "ru": "Открыть n0te",
}


NEXT_PROMPT: Dict[Lang, str] = {
    "en": "Send the next n0te or forward to the chat.",
    "uk": "Надішліть наступний n0te або перешліть у чат.",
    "ru": "Отправьте следующий n0te или перешлите в чат.",
}


PROCESSING: Dict[Lang, str] = {
    "en": "Processing...",
    "uk": "Обробляю...",
    "ru": "Обрабатываю...",
}

PROCESSING_EMOJI: str = "⏳"


PROCESSED_DONE: Dict[Lang, str] = {
    "en": "Your note was processed safely.\nOpen n0te.",
    "uk": "Ваш запис оброблено безпечно.\nВідкрийте n0te.",
    "ru": "Ваша запись обработана безопасно.\nОткройте n0te.",
}


ACCEPT_PRIVACY_FIRST: Dict[Lang, str] = {
    "en": "Please accept the Privacy Notice first.",
    "uk": "Спочатку прийміть Політику конфіденційності.",
    "ru": "Сначала примите Политику конфиденциальности.",
}

# Side menu commands descriptions per language
COMMANDS_DESC: Dict[Lang, Dict[str, str]] = {
    "en": {
        "n0te": "Open my n0te",
        "billing": "Billing and subscription",
        "privacy": "Privacy policy",
        "delete": "Delete account",
    },
    "uk": {
        "n0te": "Відкрити мій n0te",
        "billing": "Оплата та підписка",
        "privacy": "Політика конфіденційності",
        "delete": "Видалити акаунт",
    },
    "ru": {
        "n0te": "Открыть мой n0te",
        "billing": "Оплата и подписка",
        "privacy": "Политика конфиденциальности",
        "delete": "Удалить аккаунт",
    },
}

# Replies for commands
CMD_NOTE_REPLY: Dict[Lang, str] = {
    "en": "Open n0te.",
    "uk": "Відкрити мій n0te.",
    "ru": "Открыть мой n0te.",
}

CMD_BILLING_REPLY: Dict[Lang, str] = {
    "en": "Subscription status: see menu.",
    "uk": "Статус підписки: у меню.",
    "ru": "Статус подписки: в меню.",
}

CMD_DELETE_REPLY: Dict[Lang, str] = {
    "en": "Account deletion will be available soon.",
    "uk": "Видалення акаунта незабаром буде доступним.",
    "ru": "Удаление аккаунта скоро будет доступно.",
}
