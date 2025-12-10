import asyncpg

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from services.masters_service import get_master_by_id
from services.reviews_service import add_review

router = Router()


class ReviewStates(StatesGroup):
    rating = State()
    text = State()
    confirm = State()


@router.callback_query(F.data.startswith("review:add:"))
async def review_add_start(callback: CallbackQuery, state: FSMContext):
    """
    Старт формы отзыва по кнопке "Оставить отзыв" в карточке мастера.
    """
    _, _, master_id_str = callback.data.split(":", 2)
    master_id = int(master_id_str)

    await state.clear()
    await state.update_data(master_id=master_id)

    await callback.message.answer(
        "Оцените мастера по шкале от 1 до 5 (отправьте число)."
    )
    await callback.answer()
    await state.set_state(ReviewStates.rating)


@router.message(ReviewStates.rating)
async def review_rating(message: Message, state: FSMContext):
    try:
        rating = int(message.text.strip())
    except ValueError:
        await message.answer("Пожалуйста, отправьте число от 1 до 5.")
        return

    if rating < 1 or rating > 5:
        await message.answer("Рейтинг должен быть от 1 до 5.")
        return

    await state.update_data(rating=rating)
    await message.answer("Напишите текст отзыва:")
    await state.set_state(ReviewStates.text)


@router.message(ReviewStates.text)
async def review_text(message: Message, state: FSMContext):
    await state.update_data(text=message.text.strip())
    data = await state.get_data()
    await message.answer(
        f"Вы собираетесь оставить отзыв с рейтингом {data['rating']}.\n"
        "Если всё верно — отправьте 'Да'. Для отмены — 'Отмена'."
    )
    await state.set_state(ReviewStates.confirm)


@router.message(ReviewStates.confirm)
async def review_confirm(
    message: Message,
    state: FSMContext,
    db_pool: asyncpg.Pool,
):
    text = message.text.strip().lower()
    if text not in ("да", "yes", "y"):
        await message.answer("Оставление отзыва отменено.")
        await state.clear()
        return

    data = await state.get_data()
    master_id = data["master_id"]
    rating = data["rating"]
    review_text = data["text"]

    master = await get_master_by_id(db_pool, master_id)
    if not master:
        await message.answer("Мастер не найден, отзыв не сохранён.")
        await state.clear()
        return

    await add_review(
        pool=db_pool,
        master_id=master_id,
        user_id=message.from_user.id,
        username=message.from_user.username,
        rating=rating,
        text=review_text,
    )

    await message.answer("Спасибо! Ваш отзыв отправлен и учтён в рейтинге мастера.")
    await state.clear()
