import asyncio
import logging
from pathlib import Path
import sys

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand

# Support both `python -m app.main` and direct `python app/main.py`
try:  # package-style imports (preferred)
    from .config import settings
    from .handlers import start_router, misc_router, commands_router, notes_router
    from .supabase_client import get_supabase
except ImportError:
    # If run as a file, ensure project root is on sys.path
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from app.config import settings  # type: ignore
    from app.handlers import start_router, misc_router, commands_router, notes_router  # type: ignore
    from app.supabase_client import get_supabase  # type: ignore


async def set_bot_commands(bot: Bot) -> None:
    commands = [
        BotCommand(command="start", description="Начать"),
        BotCommand(command="help", description="Помощь"),
        BotCommand(command="ping", description="Проверка ответа"),
    ]
    await bot.set_my_commands(commands)


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # Routers
    dp.include_router(start_router)
    dp.include_router(misc_router)
    dp.include_router(commands_router)
    dp.include_router(notes_router)

    # Initialize Supabase client (no queries yet)
    supabase = get_supabase()
    if supabase is not None:
        dp.workflow_data["supabase"] = supabase

    await set_bot_commands(bot)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
