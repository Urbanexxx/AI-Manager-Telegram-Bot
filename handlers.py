"""Обработчики Telegram (aiogram 3.x): /start, /reset и текстовые сообщения.

Поток обработки обычного сообщения:
    1. показываем клиенту индикатор «печатает…»;
    2. get_ai_response() достаёт историю из БД и получает ответ (ИИ или mock);
    3. отправляем ответ клиенту;
    4. сохраняем в БД вопрос (role="user") и ответ (role="assistant").

Сохранение идёт ПОСЛЕ ответа, поэтому в контекст запроса новое сообщение
не попадает дважды, а при ошибке ИИ в истории не остаётся «висящих» реплик.
"""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from aiogram.utils.chat_action import ChatActionSender

from ai_integration import STORE_NAME, get_ai_response
from database import clear_history, save_message

logger = logging.getLogger(__name__)

router = Router(name="sales_manager")

TELEGRAM_MESSAGE_LIMIT = 4096

START_TEXT = (
    "Здравствуйте{name}! 👋\n\n"
    f"Я ИИ-менеджер магазина {STORE_NAME}. Помогу подобрать технику, расскажу о ценах "
    "и наличии, условиях доставки и оплаты, гарантии и действующих скидках.\n\n"
    "Задайте любой вопрос, например:\n"
    "• Какие у вас есть наушники?\n"
    "• Сколько стоит доставка?\n"
    "• Есть ли сейчас скидки?\n\n"
    "Чтобы начать диалог с чистого листа, отправьте /reset."
)

RESET_TEXT = "Готово, историю диалога я очистил. О чём хотите узнать?"

ERROR_TEXT = (
    "Извините, произошла техническая ошибка. Попробуйте повторить вопрос чуть позже."
)

UNSUPPORTED_TEXT = (
    "Я умею отвечать только на текстовые вопросы. "
    "Напишите, что вас интересует, или отправьте /start."
)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Приветствие и подсказка, о чём можно спросить."""
    first_name = message.from_user.first_name if message.from_user else ""
    await message.answer(START_TEXT.format(name=f", {first_name}" if first_name else ""))


@router.message(Command("reset"))
async def cmd_reset(message: Message) -> None:
    """Очищает историю диалога текущего пользователя."""
    if message.from_user is None:
        return
    await clear_history(message.from_user.id)
    await message.answer(RESET_TEXT)


@router.message(F.text & ~F.text.startswith("/"))
async def handle_text(message: Message) -> None:
    """Любой обычный текст: ответ менеджера + сохранение диалога в БД."""
    if message.from_user is None or message.text is None:
        return

    user_id = message.from_user.id
    question = message.text.strip()

    try:
        # Индикатор «печатает…» поддерживается всё время, пока ждём ответ нейросети
        async with ChatActionSender.typing(bot=message.bot, chat_id=message.chat.id):
            answer = await get_ai_response(user_id, question)
    except Exception:
        logger.exception("Не удалось получить ответ для user_id=%s", user_id)
        await message.answer(ERROR_TEXT)
        return

    await message.answer(answer[:TELEGRAM_MESSAGE_LIMIT])

    # Сбой записи в БД не должен ломать диалог: клиент уже получил ответ
    try:
        await save_message(user_id, "user", question)
        await save_message(user_id, "assistant", answer)
    except Exception:
        logger.exception("Не удалось сохранить историю для user_id=%s", user_id)


@router.message()
async def handle_unsupported(message: Message) -> None:
    """Стикеры, фото, голосовые и неизвестные команды."""
    await message.answer(UNSUPPORTED_TEXT)
