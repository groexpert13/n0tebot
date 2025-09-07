from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router(name=__name__)


@router.message(Command("ping"))
async def cmd_ping(message: Message) -> None:
    await message.answer("pong")


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    text = (
        "/start — приветствие\n"
        "/ping — проверка ответа бота\n"
        "/help — это сообщение"
    )
    await message.answer(text)

