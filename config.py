"""Настройки проекта: токены, пути, параметры ИИ и памяти диалога.

Все секреты читаются из переменных окружения (файл .env), поэтому
в репозиторий они не попадают. Остальные модули импортируют готовый
объект `settings`:

    from config import settings
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

SUPPORTED_PROVIDERS = ("openai", "anthropic")


class ConfigError(RuntimeError):
    """Ошибка конфигурации: не задана или неверно задана переменная окружения."""


def _require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigError(
            f"Переменная окружения {name} не задана. "
            f"Скопируйте .env.example в .env и заполните её."
        )
    return value


def _optional(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


@dataclass(frozen=True)
class Settings:
    # Telegram
    telegram_token: str

    # ИИ-провайдер: "openai" или "anthropic"
    ai_provider: str
    ai_api_key: str  # пустая строка = ключ не задан -> mock-режим
    ai_model: str
    ai_max_tokens: int
    ai_temperature: float

    # Память диалога: сколько последних сообщений (user + assistant) помнит бот
    history_limit: int

    # Пути к файлам
    db_path: Path
    knowledge_base_path: Path

    @property
    def mock_mode(self) -> bool:
        """True, если API-ключ выбранного провайдера не задан."""
        return not self.ai_api_key


def load_settings() -> Settings:
    provider = _optional("AI_PROVIDER", "openai").lower()
    if provider not in SUPPORTED_PROVIDERS:
        raise ConfigError(
            f"AI_PROVIDER='{provider}' не поддерживается. "
            f"Доступно: {', '.join(SUPPORTED_PROVIDERS)}."
        )

    # Ключ ИИ необязателен: если он пуст, бот работает в mock-режиме (см. ai_integration.py)
    if provider == "openai":
        api_key = _optional("OPENAI_API_KEY")
        model = _optional("OPENAI_MODEL", "gpt-4o-mini")
    else:
        api_key = _optional("ANTHROPIC_API_KEY")
        model = _optional("ANTHROPIC_MODEL", "claude-sonnet-5-5")

    db_path = BASE_DIR / _optional("DB_PATH", "data/bot.db")
    db_path.parent.mkdir(parents=True, exist_ok=True)

    return Settings(
        telegram_token=_require("TELEGRAM_BOT_TOKEN"),
        ai_provider=provider,
        ai_api_key=api_key,
        ai_model=model,
        ai_max_tokens=int(_optional("AI_MAX_TOKENS", "600")),
        ai_temperature=float(_optional("AI_TEMPERATURE", "0.3")),
        history_limit=int(_optional("HISTORY_LIMIT", "6")),
        db_path=db_path,
        knowledge_base_path=BASE_DIR / _optional("KNOWLEDGE_BASE_PATH", "knowledge_base.txt"),
    )


settings = load_settings()
