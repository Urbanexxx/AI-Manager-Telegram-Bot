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
    
    # Регистрируем вебхук на старте
    async def on_startup_webhook(bot: Bot) -> None:
        await on_startup(bot) # Вызовет вашу родную функцию (БД и логи)
        render_url = os.getenv("RENDER_EXTERNAL_URL")
        await bot.set_webhook(f"{render_url}/webhook", drop_pending_updates=True)

    dp.startup.register(on_startup_webhook)
    
    # Настраиваем веб-сервер для приема вебхуков от Telegram
    app = web.Application()
    webhook_requests_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_requests_handler.register(app, path="/webhook")
    setup_application(app, dp, bot=bot)
    
    port = int(os.getenv("PORT", 8080))
    
    try:
        await web._run_app(app, host="0.0.0.0", port=port)
    finally:
        await bot.session.close()
