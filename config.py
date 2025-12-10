import os
from dataclasses import dataclass
from typing import List

from dotenv import load_dotenv


load_dotenv()


@dataclass
class DBConfig:
    host: str
    port: int
    name: str
    user: str
    password: str


@dataclass
class BotConfig:
    token: str
    admin_ids: List[int]


@dataclass
class Config:
    bot: BotConfig
    db: DBConfig


def load_config() -> Config:
    """
    Загружает конфигурацию из переменных окружения / .env.
    Обязательные переменные:
    BOT_TOKEN, DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, ADMIN_IDS
    """
    token = os.getenv("BOT_TOKEN", "")
    if not token:
        raise RuntimeError("BOT_TOKEN is not set")

    admin_ids_str = os.getenv("ADMIN_IDS", "")
    admin_ids: List[int] = []
    if admin_ids_str:
        for part in admin_ids_str.split(","):
            part = part.strip()
            if part:
                try:
                    admin_ids.append(int(part))
                except ValueError:
                    pass

    db_config = DBConfig(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        name=os.getenv("DB_NAME", "masters_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
    )

    bot_config = BotConfig(token=token, admin_ids=admin_ids)
    return Config(bot=bot_config, db=db_config)
