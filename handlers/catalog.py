from typing import Optional
import asyncpg

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InputMediaPhoto

from keyboards.catalog import (
    catalog_filters_keyboard,
    master_card_keyboard,
    CATEGORIES,
)
from services.masters_service import get_approved_masters, get_master_by_id
from services.reviews_service import get_reviews_for_master

router = Router()
DEFAULT_CATEGORY = "Все"
DEFAULT_SORT = "rating"


async def _render_master_short(record) -> str:
    """
    Формирует короткое описание мастера для списка.
    """
    price_part = ""
    if record["price_min"] or record["price_max"]:
        p_from = record["price_min"] or ""
        p_to = record["price_max"] or ""
        price_part = f"\nЦена: {p_from}–{p_to}"
    rating = float(record["rating"] or 0)
    reviews_count = int(record["reviews_count"] or 0)
    return (
        f"#{record['id']} {record['name']} ({record['category'] or 'Без категории'})"
        f"{price_part}\nРейтинг: {rating} ({reviews_count} отзывов)"
    )


async def _render_master_full(record, reviews) -> str:
    """
    Формирует полное описание мастера для карточки.
    """
    lines = [
        f"<b>{record['name']}</b>",
        f"Категория: {record['category'] or '-'}",
        "",
        record["description"] or "",
    ]

    if record["price_min"] or record["price_max"]:
        lines.append(
            f"Цена: {record['price_min'] or ''}–{record['price_max'] or ''}"
        )

    contact_lines = []
    if record["phone"]:
        contact_lines.append(f"Телефон: {record['phone']}")
    if record["username"]:
        contact_lines.append(f"Telegram: @{record['username']}")
    if contact_lines:
        lines.append("")
        lines.extend(contact_lines)

    rating = float(record["rating"] or 0)
    reviews_count = int(record["reviews_count"] or 0)
    lines.append(f"\nРейтинг: {rating} ({reviews_count} отзывов)")

    if reviews:
        lines.append("\nПоследние отзывы:")
        for r in reviews:
            u = r["username"] or r["user_id"]
            lines.append(f"⭐ {r['rating']} от {u}: {r['text'][:80]}")

    return "\n".join(lines)


async def _get_masters_for_view(
    db_pool: asyncpg.Pool,
    category: str,
    sort_key: str,
    limit: int = 50,
):
    return await get_approved_masters(
        db_pool,
        category=category if category != DEFAULT_CATEGORY else None,
        sort_by=sort_key,  # type: ignore[arg-type]
        limit=limit,
    )


async def _send_master_card(
    target_message: Message,
    master,
    reviews,
    category: str,
    sort_key: str,
    index: int,
    total: int,
    send_new: bool = False,
):
    """
    Показать карточку мастера: либо новым сообщением, либо редактируя текущее.
    """
    text = await _render_master_full(master, reviews)
    keyboard = master_card_keyboard(master["id"], category, sort_key, index, total)

    target_has_photo = bool(target_message.photo)
    master_has_photo = bool(master["photo_file_id"])

    if not send_new and master_has_photo != target_has_photo:
        send_new = True

    if master_has_photo:
        if send_new:
            await target_message.answer_photo(
                photo=master["photo_file_id"],
                caption=text,
                reply_markup=keyboard,
            )
        else:
            try:
                await target_message.edit_media(
                    media=InputMediaPhoto(
                        media=master["photo_file_id"],
                        caption=text,
                    ),
                    reply_markup=keyboard,
                )
            except Exception:
                await target_message.answer_photo(
                    photo=master["photo_file_id"],
                    caption=text,
                    reply_markup=keyboard,
                )
    else:
        if send_new:
            await target_message.answer(
                text,
                reply_markup=keyboard,
            )
        else:
            try:
                await target_message.edit_text(
                    text,
                    reply_markup=keyboard,
                )
            except Exception:
                await target_message.answer(
                    text,
                    reply_markup=keyboard,
                )


@router.message(F.text == "Каталог мастеров")
async def catalog_entry(message: Message, db_pool: asyncpg.Pool):
    """
    Вход в каталог: показываем краткий список по дефолту (Все, сортировка по рейтингу).
    """
    masters = await get_approved_masters(
        db_pool, category=None, sort_by=DEFAULT_SORT
    )
    if not masters:
        await message.answer(
            "Пока нет одобренных мастеров. Попробуйте позже."
        )
        return

    text_lines = ["Каталог мастеров (топ 10):", ""]
    for m in masters:
        text_lines.append(await _render_master_short(m))

    await message.answer(
        "\n".join(text_lines),
        reply_markup=catalog_filters_keyboard(
            current_category=DEFAULT_CATEGORY, current_sort=DEFAULT_SORT
        ),
    )
    await message.answer(
        "Чтобы посмотреть карточку мастера отправьте в чат его ID или нажмите Смотреть мастеров\n Например: #1"
    )


@router.callback_query(F.data.startswith("catalog:cat:"))
async def catalog_change_category(
    callback: CallbackQuery,
    db_pool: asyncpg.Pool,
):
    """
    Смена категории фильтра.
    """
    _, _, category = callback.data.split(":", 2)

    masters = await get_approved_masters(
        db_pool,
        category=category if category != DEFAULT_CATEGORY else None,
        sort_by=DEFAULT_SORT,
    )

    if not masters:
        await callback.message.edit_text(
            f"Мастера в категории «{category}» пока не найдены.",
            reply_markup=catalog_filters_keyboard(
                current_category=category, current_sort=DEFAULT_SORT
            ),
        )
        await callback.answer()
        return

    text_lines = [f"Каталог мастеров — {category}", ""]
    for m in masters:
        text_lines.append(await _render_master_short(m))

    await callback.message.edit_text(
        "\n".join(text_lines),
        reply_markup=catalog_filters_keyboard(
            current_category=category, current_sort=DEFAULT_SORT
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("catalog:sort:"))
async def catalog_change_sort(
    callback: CallbackQuery,
    db_pool: asyncpg.Pool,
):
    """
    Смена сортировки.
    """
    _, _, sort_key = callback.data.split(":", 2)

    # попытаемся извлечь последнюю выбранную категорию из текста (упрощённо)
    text = callback.message.text or ""
    current_category: Optional[str] = "Все"
    for cat in CATEGORIES:
        if f"— {cat}" in text or f"Каталог мастеров — {cat}" in text:
            current_category = cat
            break

    masters = await get_approved_masters(
        db_pool,
        category=current_category if current_category != DEFAULT_CATEGORY else None,
        sort_by=sort_key,  # type: ignore[arg-type]
    )

    if not masters:
        await callback.message.edit_text(
            "Подходящих мастеров не найдено.",
            reply_markup=catalog_filters_keyboard(
                current_category=current_category or DEFAULT_CATEGORY,
                current_sort=sort_key,
            ),
        )
        await callback.answer()
        return

    text_lines = [f"Каталог мастеров — {current_category}", ""]
    for m in masters:
        text_lines.append(await _render_master_short(m))

    await callback.message.edit_text(
        "\n".join(text_lines),
        reply_markup=catalog_filters_keyboard(
            current_category=current_category or DEFAULT_CATEGORY,
            current_sort=sort_key,
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("catalog:view:"))
async def catalog_view_master(
    callback: CallbackQuery,
    db_pool: asyncpg.Pool,
):
    """
    Просмотр карточки мастера и навигация по списку через inline-кнопки.
    """
    try:
        _, _, category, sort_key, index_str = callback.data.split(":", 4)
        index = int(index_str)
    except ValueError:
        await callback.answer("Не удалось открыть карточку.")
        return

    masters = await _get_masters_for_view(db_pool, category, sort_key)
    if not masters:
        await callback.answer("Мастера не найдены.")
        return

    if index < 0 or index >= len(masters):
        index = 0

    master = masters[index]
    reviews = await get_reviews_for_master(db_pool, master["id"])

    # Если нажали из списка каталога — отправляем новое сообщение, иначе редактируем карточку.
    send_new = "Каталог мастеров" in (callback.message.text or "")
    await _send_master_card(
        target_message=callback.message,
        master=master,
        reviews=reviews,
        category=category,
        sort_key=sort_key,
        index=index,
        total=len(masters),
        send_new=send_new,
    )
    await callback.answer()


@router.message(F.text.startswith("#") & F.text.regexp(r"^#\d+"))
async def show_master_by_hash(message: Message, db_pool: asyncpg.Pool):
    """
    Простой хак: если пользователь отправит #ID мастера - покажем карточку мастера.
    Например: #3
    """
    try:
        master_id = int(message.text.lstrip("#"))
    except (TypeError, ValueError):
        return

    master = await get_master_by_id(db_pool, master_id)
    if not master:
        await message.answer("Мастер не найден.")
        return

    reviews = await get_reviews_for_master(db_pool, master_id)

    masters_for_nav = await _get_masters_for_view(
        db_pool, DEFAULT_CATEGORY, DEFAULT_SORT
    )
    total = len(masters_for_nav)
    index = 0
    for idx, m in enumerate(masters_for_nav):
        if m["id"] == master_id:
            index = idx
            break
    else:
        # если запрошенный мастер не попал в топ списка — отключаем навигацию
        total = 1

    await _send_master_card(
        target_message=message,
        master=master,
        reviews=reviews,
        category=DEFAULT_CATEGORY,
        sort_key=DEFAULT_SORT,
        index=index,
        total=total if total > 0 else 1,
        send_new=True,
    )
