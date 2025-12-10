from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Базовый набор категорий, можно расширять
CATEGORIES = [
    "Все",
    "Сантехника",
    "Электрика",
    "Ремонт",
]


def catalog_filters_keyboard(
    current_category: str = "Все", current_sort: str = "rating"
) -> InlineKeyboardMarkup:
    """
    Клавиатура фильтров и сортировки каталога.
    callback_data в формате:
    - "catalog:cat:<category>"
    - "catalog:sort:<sort>"
    - "catalog:view:<category>:<sort>:<index>"
    """
    buttons_cat = []
    for cat in CATEGORIES:
        text = f"[{cat}]" if cat == current_category else cat
        buttons_cat.append(
            InlineKeyboardButton(
                text=text,
                callback_data=f"catalog:cat:{cat}",
            )
        )

    sort_buttons = [
        ("Рейтинг", "rating"),
        ("Цена", "price"),
        ("Отзывы", "reviews"),
    ]
    buttons_sort = []
    for title, key in sort_buttons:
        text = f"[{title}]" if key == current_sort else title
        buttons_sort.append(
            InlineKeyboardButton(
                text=text,
                callback_data=f"catalog:sort:{key}",
            )
        )

    view_button = InlineKeyboardButton(
        text="Смотреть мастеров",
        callback_data=f"catalog:view:{current_category}:{current_sort}:0",
    )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            buttons_cat,
            buttons_sort,
            [view_button],
        ]
    )


def master_card_keyboard(
    master_id: int,
    category: str | None = None,
    sort_key: str | None = None,
    index: int = 0,
    total: int = 1,
) -> InlineKeyboardMarkup:
    """
    Клавиатура для карточки мастера: навигация и оставить отзыв.
    """
    rows = []

    if category and sort_key and total > 1:
        prev_idx = (index - 1) % total
        next_idx = (index + 1) % total
        rows.append(
            [
                InlineKeyboardButton(
                    text="⬅️ Предыдущий",
                    callback_data=f"catalog:view:{category}:{sort_key}:{prev_idx}",
                ),
                InlineKeyboardButton(
                    text="Следующий ➡️",
                    callback_data=f"catalog:view:{category}:{sort_key}:{next_idx}",
                ),
            ]
        )

    return InlineKeyboardMarkup(
        inline_keyboard=rows
        + [
            [
                InlineKeyboardButton(
                    text="Оставить отзыв",
                    callback_data=f"review:add:{master_id}",
                )
            ]
        ]
    )
