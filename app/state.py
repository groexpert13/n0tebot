from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class UserState:
    lang: Optional[str] = None  # 'en' | 'uk' | 'ru'
    accepted_privacy: bool = False
    # ID последнего «контентного» сообщения бота (с кнопкой и подсказкой)
    last_content_message_id: Optional[int] = None
    # ID последнего сообщения-подсказки ("Отправьте следующий n0te…")
    last_prompt_message_id: Optional[int] = None


user_states: Dict[int, UserState] = {}


def get_user_state(user_id: int) -> UserState:
    state = user_states.get(user_id)
    if state is None:
        state = UserState()
        user_states[user_id] = state
    return state
