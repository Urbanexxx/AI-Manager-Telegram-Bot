import os
import logging
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from handlers import router
from config import settings
from ai_integration import load_knowledge_base
from database import init_db

async def on_startup(bot: Bot) -> None:
    """Выполняется один раз при старте: готовим БД и базу знаний."""
    await init_db()  # создаёт таблицу messages, если её ещё нет
    load_knowledge_base()  # читает knowledge_base.txt в память и логирует режим
    
    me = await bot.get_me()
    logging.info(f"Бот @{me.username} запущен в облаке Render!")

async def on_startup_webhook(bot: Bot) -> None:
    await on_startup(bot)
    render_url = os.getenv("RENDER_EXTERNAL_URL")
    await bot.set_webhook(f"{render_url}/webhook", drop_pending_updates=True)

async def main() -> None:
    bot = Bot(token=settings.telegram_token)
    dp = Dispatcher()
    dp.include_router(router)
    dp.startup.register(on_startup_webhook)
    
    app = web.Application()
    webhook_requests_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_requests_handler.register(app, path="/webhook")
    setup_application(app, dp, bot=bot)
    
    port = int(os.getenv("PORT", 8080))
    
    try:
        await web._run_app(app, host="0.0.0.0", port=port)
    finally:
        await bot.session.close()

if name == "main":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
    asyncio.run(main())
