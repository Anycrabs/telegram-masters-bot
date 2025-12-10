from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Главное меню для обычного пользователя.
    """
    kb = [
        [
            KeyboardButton(text="Каталог мастеров"),
            KeyboardButton(text="Поиск"),
        ],
        [
            KeyboardButton(text="Стать мастером"),
        ],
        [
            KeyboardButton(text="О нас"),
            KeyboardButton(text="FAQ"),
            KeyboardButton(text="Контакты"),
        ],
    ]
    return ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True,
        input_field_placeholder="Выберите пункт меню",
    )
