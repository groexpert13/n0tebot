from __future__ import annotations

from typing import List

from aiogram.types import BotCommand, BotCommandScopeChat

from .texts import COMMANDS_DESC


def make_commands(lang: str) -> List[BotCommand]:
    t = COMMANDS_DESC.get(lang, COMMANDS_DESC["en"])
    return [
        BotCommand(command="n0te", description=t["n0te"]),
        BotCommand(command="billing", description=t["billing"]),
        BotCommand(command="privacy", description=t["privacy"]),
        BotCommand(command="delete", description=t["delete"]),
    ]


async def set_chat_commands(bot, chat_id: int, lang: str) -> None:
    commands = make_commands(lang)
    await bot.set_my_commands(commands, scope=BotCommandScopeChat(chat_id=chat_id))

