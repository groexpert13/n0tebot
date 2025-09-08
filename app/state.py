from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Any, List


@dataclass
class UserState:
    lang: Optional[str] = None  # 'en' | 'uk' | 'ru'
    accepted_privacy: bool = False
    # ID последнего «контентного» сообщения бота (с кнопкой и подсказкой)
    last_content_message_id: Optional[int] = None
    # ID последнего сообщения-подсказки ("Отправьте следующий n0te…")
    last_prompt_message_id: Optional[int] = None
    # IDs of temporary processing messages ("Processing..." and hourglass)
    processing_msg_id: Optional[int] = None
    processing_emoji_msg_id: Optional[int] = None
    # Batch collection for grouping multiple incoming messages into one note
    batch_items: List[Dict[str, Any]] = field(default_factory=list)
    batch_task: Optional[Any] = None  # asyncio.Task, stored as Any to avoid import cycle
    # Per-user lock to prevent race conditions when multiple messages arrive simultaneously
    batch_lock: Optional[Any] = None  # asyncio.Lock created lazily


user_states: Dict[int, UserState] = {}


def get_user_state(user_id: int) -> UserState:
    state = user_states.get(user_id)
    if state is None:
        state = UserState()
        user_states[user_id] = state
    return state
