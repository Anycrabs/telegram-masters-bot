from typing import Optional
import asyncio
import logging

import asyncpg

from config import DBConfig

logger = logging.getLogger(__name__)


async def create_pool(db_config: DBConfig) -> asyncpg.pool.Pool:
    """
    Создаёт connection pool для PostgreSQL с обработкой ошибок и повторными попытками.
    """
    max_retries = 3
    retry_delay = 2  # секунды
    
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(
                f"Попытка подключения к БД (попытка {attempt}/{max_retries}): "
                f"{db_config.user}@{db_config.host}:{db_config.port}/{db_config.name}"
            )
            
            pool = await asyncpg.create_pool(
                host=db_config.host,
                port=db_config.port,
                user=db_config.user,
                password=db_config.password,
                database=db_config.name,
                min_size=1,
                max_size=10,
                command_timeout=30,  # таймаут выполнения команды (30 сек)
                timeout=10,  # таймаут подключения (10 сек)
                server_settings={
                    'application_name': 'tg_masters_bot',
                    'jit': 'off',  # отключаем JIT для стабильности
                },
            )
            
            # Проверяем соединение
            async with pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            
            logger.info("Успешное подключение к БД")
            return pool
            
        except (OSError, ConnectionResetError, asyncpg.exceptions.ConnectionDoesNotExistError) as e:
            error_msg = f"Ошибка подключения к БД (попытка {attempt}/{max_retries}): {e}"
            logger.error(error_msg)
            
            if attempt < max_retries:
                logger.info(f"Повторная попытка через {retry_delay} сек...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # экспоненциальная задержка
            else:
                raise ConnectionError(
                    f"Не удалось подключиться к БД после {max_retries} попыток. "
                    f"Проверьте:\n"
                    f"1. Запущен ли PostgreSQL сервер\n"
                    f"2. Правильность параметров подключения (host={db_config.host}, "
                    f"port={db_config.port}, database={db_config.name})\n"
                    f"3. Доступность сервера по сети\n"
                    f"4. Существует ли база данных '{db_config.name}'\n"
                    f"Последняя ошибка: {e}"
                ) from e
                
        except asyncpg.exceptions.InvalidPasswordError as e:
            raise ConnectionError(
                f"Неверный пароль для пользователя '{db_config.user}'. "
                f"Проверьте DB_PASSWORD в переменных окружения."
            ) from e
            
        except asyncpg.exceptions.InvalidCatalogNameError as e:
            raise ConnectionError(
                f"База данных '{db_config.name}' не существует. "
                f"Создайте её перед запуском бота."
            ) from e
            
        except Exception as e:
            logger.error(f"Неожиданная ошибка при подключении к БД: {e}")
            raise ConnectionError(
                f"Неожиданная ошибка при подключении к БД: {e}\n"
                f"Проверьте параметры подключения в .env файле."
            ) from e


async def init_db(pool: asyncpg.pool.Pool) -> None:
    """
    Простая "миграция" — создаём таблицы, если их нет.
    """
    async with pool.acquire() as conn:
        # Таблица пользователей
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT UNIQUE NOT NULL,
                role TEXT DEFAULT 'user',
                master_id INTEGER,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            """
        )

        # Таблица мастеров
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS masters (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT,
                name TEXT NOT NULL,
                username TEXT,
                phone TEXT,
                category TEXT,
                description TEXT,
                price_min INTEGER,
                price_max INTEGER,
                photo_file_id TEXT,
                photo_url TEXT,
                status TEXT DEFAULT 'new', -- new / approved / rejected / inactive
                rating NUMERIC(3, 2) DEFAULT 0,
                reviews_count INTEGER DEFAULT 0,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
            """
        )

        # Таблица отзывов
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reviews (
                id SERIAL PRIMARY KEY,
                master_id INTEGER NOT NULL REFERENCES masters(id) ON DELETE CASCADE,
                user_id BIGINT NOT NULL,
                username TEXT,
                rating SMALLINT NOT NULL CHECK (rating >= 1 AND rating <= 5),
                text TEXT,
                is_visible BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            """
        )

        # Таблица инфо-страниц
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS info_pages (
                slug TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
            """
        )

        # Таблица FAQ
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS faq (
                id SERIAL PRIMARY KEY,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                is_visible BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
            """
        )

        # Минимальные дефолтные страницы
        await conn.execute(
            """
            INSERT INTO info_pages (slug, title, content)
            VALUES 
                ('about', 'О нас', 'Информация о сервисе мастеров.'),
                ('contacts', 'Контакты администрации', 'Свяжитесь с нами в Telegram.')
            ON CONFLICT (slug) DO NOTHING;
            """
        )
