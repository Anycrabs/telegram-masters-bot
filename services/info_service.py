from typing import Optional, List

import asyncpg


async def get_info_page(pool: asyncpg.pool.Pool, slug: str) -> Optional[asyncpg.Record]:
    """
    Получить инфо-страницу по slug (about, contacts и т.п.).
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM info_pages WHERE slug = $1;",
            slug,
        )
        return row


async def update_info_page(
    pool: asyncpg.pool.Pool,
    slug: str,
    title: str,
    content: str,
) -> None:
    """
    Обновить или создать инфо-страницу.
    """
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO info_pages (slug, title, content)
            VALUES ($1,$2,$3)
            ON CONFLICT (slug) DO UPDATE
              SET title = EXCLUDED.title,
                  content = EXCLUDED.content,
                  updated_at = NOW();
            """,
            slug,
            title,
            content,
        )


async def get_faq(pool: asyncpg.pool.Pool) -> List[asyncpg.Record]:
    """
    Получить видимые FAQ.
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT *
            FROM faq
            WHERE is_visible = TRUE
            ORDER BY created_at ASC;
            """
        )
        return list(rows)


async def add_faq(
    pool: asyncpg.pool.Pool,
    question: str,
    answer: str,
) -> None:
    """
    Добавить новый вопрос-ответ.
    """
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO faq (question, answer, is_visible)
            VALUES ($1,$2,TRUE);
            """,
            question,
            answer,
        )
