from typing import List, Optional

import asyncpg


async def add_review(
    pool: asyncpg.pool.Pool,
    master_id: int,
    user_id: int,
    username: Optional[str],
    rating: int,
    text: str,
) -> None:
    """
    Добавить отзыв и обновить кэш рейтинга мастера.
    """
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                """
                INSERT INTO reviews (master_id, user_id, username, rating, text)
                VALUES ($1,$2,$3,$4,$5);
                """,
                master_id,
                user_id,
                username,
                rating,
                text,
            )

            # Пересчёт рейтинга
            row = await conn.fetchrow(
                """
                SELECT
                    COALESCE(AVG(rating), 0) AS avg_rating,
                    COUNT(*) AS cnt
                FROM reviews
                WHERE master_id = $1
                  AND is_visible = TRUE;
                """,
                master_id,
            )
            avg_rating = float(row["avg_rating"]) if row["avg_rating"] is not None else 0.0
            cnt = int(row["cnt"])

            await conn.execute(
                """
                UPDATE masters
                SET rating = $2,
                    reviews_count = $3,
                    updated_at = NOW()
                WHERE id = $1;
                """,
                master_id,
                avg_rating,
                cnt,
            )


async def get_reviews_for_master(
    pool: asyncpg.pool.Pool,
    master_id: int,
    limit: int = 5,
) -> List[asyncpg.Record]:
    """
    Получить последние отзывы по мастеру.
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT *
            FROM reviews
            WHERE master_id = $1 AND is_visible = TRUE
            ORDER BY created_at DESC
            LIMIT $2;
            """,
            master_id,
            limit,
        )
        return list(rows)
