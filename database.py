"""Работа с SQLite: хранение истории диалогов для памяти бота.

Используется aiosqlite, чтобы запросы к базе не блокировали event loop aiogram.
Таблица создаётся автоматически при первом обращении к базе
(явный вызов init_db() при старте бота тоже допустим, но не обязателен).

Публичный API:
    await init_db()
    await save_message(user_id, role, content)
    await get_chat_history(user_id, limit=6) -> [{"role": ..., "content": ...}, ...]
    await clear_history(user_id)
"""
from __future__ import annotations

import asyncio

import aiosqlite

from config import settings

VALID_ROLES = ("user", "assistant")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id   INTEGER NOT NULL,
    role      TEXT    NOT NULL CHECK (role IN ('user', 'assistant')),
    content   TEXT    NOT NULL,
    timestamp TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_messages_user_id_id
    ON messages (user_id, id);
"""

_schema_ready = False
_schema_lock = asyncio.Lock()


async def init_db() -> None:
    """Создаёт таблицу и индекс, если их ещё нет. Безопасно вызывать повторно."""
    global _schema_ready
    if _schema_ready:
        return
    async with _schema_lock:
        if _schema_ready:  # другой таск мог успеть создать схему, пока мы ждали
            return
        async with aiosqlite.connect(settings.db_path) as db:
            await db.executescript(_SCHEMA)
            await db.commit()
        _schema_ready = True


async def save_message(user_id: int, role: str, content: str) -> None:
    """Сохраняет сообщение пользователя (role='user') или ответ ИИ (role='assistant')."""
    if role not in VALID_ROLES:
        raise ValueError(f"role должна быть одной из {VALID_ROLES}, получено: {role!r}")

    await init_db()
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute(
            "INSERT INTO messages (user_id, role, content) VALUES (?, ?, ?)",
            (user_id, role, content),
        )
        await db.commit()


async def get_chat_history(
    user_id: int, limit: int = settings.history_limit
) -> list[dict[str, str]]:
    """Возвращает последние `limit` сообщений пользователя в хронологическом порядке.

    Формат ответа совместим с OpenAI и Anthropic:
        [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
    """
    await init_db()
    async with aiosqlite.connect(settings.db_path) as db:
        # Берём самые свежие (DESC), затем разворачиваем в порядок «старые -> новые».
        # Сортируем по id, а не по timestamp: у timestamp точность до секунды,
        # и сообщения, сохранённые в одну секунду, могли бы перепутаться.
        async with db.execute(
            "SELECT role, content FROM messages "
            "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ) as cursor:
            rows = await cursor.fetchall()

    return [{"role": role, "content": content} for role, content in reversed(rows)]


async def clear_history(user_id: int) -> None:
    """Удаляет всю историю пользователя (пригодится для команды /reset)."""
    await init_db()
    async with aiosqlite.connect(settings.db_path) as db:
        await db.execute("DELETE FROM messages WHERE user_id = ?", (user_id,))
        await db.commit()
