"""
Middleware для передачи db_pool и config в хендлеры.
"""
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject


class DatabaseMiddleware(BaseMiddleware):
    """
    Middleware для добавления db_pool и config в data для всех хендлеров.
    """

    def __init__(self, db_pool, config):
        self.db_pool = db_pool
        self.config = config

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        """
        Добавляет db_pool и config в data перед вызовом хендлера.
        """
        data["db_pool"] = self.db_pool
        data["config"] = self.config
        return await handler(event, data)