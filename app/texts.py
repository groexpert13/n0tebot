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
    "en": "Please review and accept our Privacy Notice: {url}",
    "uk": "Будь ласка, перегляньте та прийміть нашу Політику конфіденційності: {url}",
    "ru": "Пожалуйста, ознакомьтесь и примите нашу Политику конфиденциальности: {url}",
}

PRIVACY_ACCEPT_BUTTON: Dict[Lang, str] = {
    "en": "I accept",
    "uk": "Приймаю",
    "ru": "Принимаю",
}

PRIVACY_ALERT: Dict[Lang, str] = {
    "en": (
        "Your data is protected from third parties, except the AI used for processing.\n"
        "Do not send data that may compromise you."
    ),
    "uk": (
        "Ваші дані захищені від третіх осіб, окрім AI, який використовується для обробки.\n"
        "Не надсилайте дані, що можуть вас скомпрометувати."
    ),
    "ru": (
        "Ваши данные защищены от третьих лиц, кроме ИИ, используемого для обработки.\n"
        "Не отправляйте данные, которые могут вас скомпрометировать."
    ),
}


PRO_MESSAGE: Dict[Lang, str] = {
    "en": (
        "Pro (trial) — 7 days\n"
        "Send or forward audio or text for processing.\n"
        "Records are protected from third parties, except the AI used for processing.\n\n"
        "Do not send data that may compromise you.\n\n"
        "Open n0te.\n\n"
        "Subscription status: see menu."
    ),
    "uk": (
        "Pro (trial) — 7 днів\n"
        "Записуйте або пересилайте аудіо чи текст для обробки.\n"
        "Записи захищені від третіх осіб, окрім AI, який використовується для обробки.\n\n"
        "Не надсилайте дані, що можуть вас скомпрометувати.\n\n"
        "Відкрийте n0te.\n\n"
        "Статус підписки: у меню."
    ),
    "ru": (
        "Pro (trial) — 7 дней\n"
        "Отправляйте или пересылайте аудио или текст для обработки.\n"
        "Записи защищены от третьих лиц, кроме ИИ, используемого для обработки.\n\n"
        "Не отправляйте данные, которые могут вас скомпрометировать.\n\n"
        "Откройте n0te.\n\n"
        "Статус подписки: в меню."
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
    "en": "⏳ Processing...",
    "uk": "⏳ Обробляю...",
    "ru": "⏳ Обрабатываю...",
}


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
