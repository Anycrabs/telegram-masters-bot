import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import load_config
from db.db import create_pool, init_db
from handlers import common, catalog, master, admin, reviews, info
from middleware import DatabaseMiddleware

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """
    Точка входа в приложение.
    Инициализирует бота, БД, регистрирует роутеры и запускает polling.
    """
    config = load_config()
    logger.info("Запуск бота...")

    bot = Bot(
        token=config.bot.token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # FSM-хранилище в памяти
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Создаём connection pool для БД
    try:
        db_pool = await create_pool(config.db)
        # Инициализация схемы БД
        await init_db(db_pool)
        logger.info("База данных инициализирована")
    except Exception as e:
        logger.error(f"Критическая ошибка при инициализации БД: {e}")
        raise

    # Регистрируем middleware для передачи db_pool и config в хендлеры
    dp.message.middleware(DatabaseMiddleware(db_pool, config))
    dp.callback_query.middleware(DatabaseMiddleware(db_pool, config))

    # Регистрируем роутеры
    dp.include_router(common.router)
    dp.include_router(catalog.router)
    dp.include_router(master.router)
    dp.include_router(admin.router)
    dp.include_router(reviews.router)
    dp.include_router(info.router)

    # Запуск бота
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
