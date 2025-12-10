from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def admin_main_keyboard() -> InlineKeyboardMarkup:
    """
    Главное меню админа.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Заявки мастеров", callback_data="admin:masters:pending"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Все мастера", callback_data="admin:masters:all"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Инфо-разделы", callback_data="admin:info:menu"
                )
            ],
            [
                InlineKeyboardButton(
                    text="FAQ", callback_data="admin:faq:menu"
                )
            ],
        ]
    )


def admin_pending_master_keyboard(master_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура для заявки мастера (одобрить / отклонить).
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Одобрить",
                    callback_data=f"admin:masters:approve:{master_id}",
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data=f"admin:masters:reject:{master_id}",
                ),
            ]
        ]
    )


def admin_info_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Меню управления инфо-разделами.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="О нас", callback_data="admin:info:edit:about")
            ],
            [
                InlineKeyboardButton(
                    text="Контакты", callback_data="admin:info:edit:contacts"
                )
            ],
        ]
    )


def admin_faq_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Меню управления FAQ.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Добавить вопрос-ответ",
                    callback_data="admin:faq:add",
                )
            ]
        ]
    )
