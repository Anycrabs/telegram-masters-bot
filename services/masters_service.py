from typing import List, Optional, Literal, Any

import asyncpg


SortBy = Literal["rating", "price", "reviews"]


async def create_master_application(
    pool: asyncpg.pool.Pool,
    telegram_id: int,
    name: str,
    username: Optional[str],
    phone: str,
    category: str,
    description: str,
    price_min: Optional[int],
    price_max: Optional[int],
    photo_file_id: Optional[str],
) -> int:
    """
    Создаёт заявку мастера со статусом 'new'.
    Возвращает id мастера.
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO masters (
                telegram_id, name, username, phone, category,
                description, price_min, price_max, photo_file_id, status
            )
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,'new')
            RETURNING id;
            """,
            telegram_id,
            name,
            username,
            phone,
            category,
            description,
            price_min,
            price_max,
            photo_file_id,
        )
        return int(row["id"])


async def get_approved_masters(
    pool: asyncpg.pool.Pool,
    category: Optional[str] = None,
    price_min: Optional[int] = None,
    price_max: Optional[int] = None,
    sort_by: SortBy = "rating",
    limit: int = 10,
) -> List[asyncpg.Record]:
    """
    Получить список одобренных мастеров с фильтрами и сортировкой.
    """
    async with pool.acquire() as conn:
        conditions = ["status = 'approved'"]
        params: list[Any] = []
        idx = 1

        if category and category != "Все":
            conditions.append(f"category = ${idx}")
            params.append(category)
            idx += 1

        if price_min is not None:
            conditions.append(f"price_min >= ${idx}")
            params.append(price_min)
            idx += 1

        if price_max is not None:
            conditions.append(f"price_max <= ${idx}")
            params.append(price_max)
            idx += 1

        where_clause = " AND ".join(conditions) if conditions else "TRUE"

        if sort_by == "price":
            order_by = "price_min ASC NULLS LAST"
        elif sort_by == "reviews":
            order_by = "reviews_count DESC, rating DESC"
        else:
            order_by = "rating DESC, reviews_count DESC"

        query = f"""
        SELECT *
        FROM masters
        WHERE {where_clause}
        ORDER BY {order_by}
        LIMIT {limit};
        """

        rows = await conn.fetch(query, *params)
        return list(rows)


async def get_master_by_id(pool: asyncpg.pool.Pool, master_id: int) -> Optional[asyncpg.Record]:
    """
    Получить мастера по id.
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM masters WHERE id = $1;",
            master_id,
        )
        return row


async def search_masters(
    pool: asyncpg.pool.Pool,
    text: str,
    limit: int = 10,
) -> List[asyncpg.Record]:
    """
    Поиск мастеров по имени/описанию/категории (simple ILIKE).
    """
    pattern = f"%{text}%"
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT *
            FROM masters
            WHERE status = 'approved'
              AND (
                name ILIKE $1
                OR description ILIKE $1
                OR category ILIKE $1
              )
            ORDER BY rating DESC, reviews_count DESC
            LIMIT $2;
            """,
            pattern,
            limit,
        )
        return list(rows)


async def get_pending_masters(pool: asyncpg.pool.Pool) -> List[asyncpg.Record]:
    """
    Получить мастеров со статусом new.
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM masters
            WHERE status = 'new'
            ORDER BY created_at ASC;
            """
        )
        return list(rows)


async def set_master_status(
    pool: asyncpg.pool.Pool,
    master_id: int,
    status: str,
) -> None:
    """
    Обновить статус мастера.
    """
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE masters
            SET status = $2,
                updated_at = NOW()
            WHERE id = $1;
            """,
            master_id,
            status,
        )


async def get_all_masters(pool: asyncpg.pool.Pool, category: Optional[str] = None) -> List[asyncpg.Record]:
    """
    Получить всех мастеров, опционально по категории.
    """
    async with pool.acquire() as conn:
        if category and category != "Все":
            rows = await conn.fetch(
                """
                SELECT * FROM masters
                WHERE category = $1
                ORDER BY created_at DESC;
                """,
                category,
            )
        else:
            rows = await conn.fetch(
                """
                SELECT * FROM masters
                ORDER BY created_at DESC;
                """
            )
        return list(rows)
