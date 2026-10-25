"""Точка входа: python main.py"""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher

from ai_integration import load_knowledge_base
from config import settings
from database import init_db
from handlers import router

logger = logging.getLogger(__name__)


async def on_startup(bot: Bot) -> None:
    """Выполняется один раз при старте: готовим БД и базу знаний."""
    await init_db()          # создаёт таблицу messages, если её ещё нет
    load_knowledge_base()    # читает knowledge_base.txt в память (и логирует режим ИИ)

    me = await bot.get_me()
    logger.info("Бот @%s запущен. Остановка: Ctrl+C", me.username)


async def main() -> None:
    bot = Bot(token=settings.telegram_token)
    dp = Dispatcher()
    dp.include_router(router)
    dp.startup.register(on_startup)

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен")
