from typing import Optional
import asyncpg

from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from keyboards.catalog import CATEGORIES
from services.masters_service import create_master_application
from config import Config

router = Router()


class MasterApplicationStates(StatesGroup):
    name = State()
    phone = State()
    username = State()
    category = State()
    description = State()
    price_range = State()
    photo = State()
    confirm = State()


@router.message(F.text == "Стать мастером")
async def become_master_start(message: Message, state: FSMContext):
    """
    Старт формы добавления мастера.
    """
    await state.clear()
    await message.answer(
        "Заполним заявку мастера.\n\n"
        "Для начала, как вас зовут? (Введите имя)",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(MasterApplicationStates.name)


@router.message(MasterApplicationStates.name)
async def master_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await message.answer("Укажите контактный телефон:")
    await state.set_state(MasterApplicationStates.phone)


@router.message(MasterApplicationStates.phone)
async def master_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text.strip())
    await message.answer(
        "Укажите ваш Telegram username (без @). Если нет — напишите '-'."
    )
    await state.set_state(MasterApplicationStates.username)


@router.message(MasterApplicationStates.username)
async def master_username(message: Message, state: FSMContext):
    username = message.text.strip()
    if username == "-":
        username = None
    await state.update_data(username=username)

    cats_text = "\n".join(f"- {c}" for c in CATEGORIES if c != "Все")
    await message.answer(
        "Выберите категорию из списка или введите свою:\n" + cats_text
    )
    await state.set_state(MasterApplicationStates.category)


@router.message(MasterApplicationStates.category)
async def master_category(message: Message, state: FSMContext):
    category = message.text.strip()
    await state.update_data(category=category)
    await message.answer(
        "Кратко опишите ваши услуги (что делаете, с чем работаете):"
    )
    await state.set_state(MasterApplicationStates.description)


@router.message(MasterApplicationStates.description)
async def master_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    await message.answer(
        "Укажите примерный диапазон цен в формате 'мин макс' (например, '1000 5000').\n"
        "Если не хотите указывать — отправьте '-'."
    )
    await state.set_state(MasterApplicationStates.price_range)


@router.message(MasterApplicationStates.price_range)
async def master_price_range(message: Message, state: FSMContext):
    text = message.text.strip()
    price_min: Optional[int] = None
    price_max: Optional[int] = None

    if text != "-":
        parts = text.replace(",", " ").split()
        if len(parts) >= 1:
            try:
                price_min = int(parts[0])
            except ValueError:
                price_min = None
        if len(parts) >= 2:
            try:
                price_max = int(parts[1])
            except ValueError:
                price_max = None

    await state.update_data(price_min=price_min, price_max=price_max)
    await message.answer(
        "Пришлите, пожалуйста, ваше фото / фото работ (по желанию).\n"
        "Если не хотите — отправьте '-'."
    )
    await state.set_state(MasterApplicationStates.photo)


@router.message(MasterApplicationStates.photo)
async def master_photo(message: Message, state: FSMContext):
    photo_file_id: Optional[str] = None

    if message.photo:
        # берём самое большое по размеру фото
        photo_file_id = message.photo[-1].file_id
    elif message.text and message.text.strip() == "-":
        photo_file_id = None
    else:
        await message.answer("Отправьте фото или '-' для пропуска.")
        return

    await state.update_data(photo_file_id=photo_file_id)

    data = await state.get_data()
    text_preview = (
        "Проверьте данные заявки:\n\n"
        f"Имя: {data.get('name')}\n"
        f"Телефон: {data.get('phone')}\n"
        f"Username: {data.get('username') or '-'}\n"
        f"Категория: {data.get('category')}\n"
        f"Описание: {data.get('description')}\n"
        f"Цены: {data.get('price_min') or ''}–{data.get('price_max') or ''}\n"
        f"Фото: {'есть' if data.get('photo_file_id') else 'нет'}\n\n"
        "Если всё верно — отправьте 'Да'. Для отмены — 'Отмена'."
    )

    await message.answer(text_preview)
    await state.set_state(MasterApplicationStates.confirm)


@router.message(MasterApplicationStates.confirm)
async def master_confirm(
    message: Message,
    state: FSMContext,
    db_pool: asyncpg.Pool,
    config: Config,
):
    text = message.text.strip().lower()
    if text not in ("да", "yes", "y"):
        await message.answer("Заявка отменена.")
        await state.clear()
        return

    data = await state.get_data()
    master_id = await create_master_application(
        pool=db_pool,
        telegram_id=message.from_user.id,
        name=data["name"],
        username=data.get("username"),
        phone=data["phone"],
        category=data["category"],
        description=data["description"],
        price_min=data.get("price_min"),
        price_max=data.get("price_max"),
        photo_file_id=data.get("photo_file_id"),
    )

    # Уведомим админов (простое оповещение)
    for admin_id in config.bot.admin_ids:
        try:
            await message.bot.send_message(
                admin_id,
                f"Новая заявка мастера #{master_id} от @{message.from_user.username or message.from_user.id}.",
            )
        except Exception:
            pass

    await message.answer(
        "Ваша заявка отправлена на модерацию. "
        "После одобрения вы получите уведомление.",
    )
    await state.clear()
