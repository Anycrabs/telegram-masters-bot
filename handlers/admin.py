from typing import List

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from asyncpg.pool import Pool
from config import Config

from keyboards.admin import (
    admin_main_keyboard,
    admin_pending_master_keyboard,
    admin_info_menu_keyboard,
    admin_faq_menu_keyboard,
)
from services.masters_service import (
    get_pending_masters,
    get_master_by_id,
    set_master_status,
    get_all_masters,
)
from services.info_service import (
    get_info_page,
    update_info_page,
    add_faq,
)

router = Router()


def _is_admin(user_id: int, config: Config) -> bool:
    """
    Проверка, является ли пользователь администратором.
    """
    return user_id in config.bot.admin_ids


class InfoEditStates(StatesGroup):
    slug = State()
    title = State()
    content = State()


class FAQAddStates(StatesGroup):
    question = State()
    answer = State()


# ======================
#   /admin — вход
# ======================

@router.message(Command("admin"))
async def admin_panel(message: Message, config: Config):
    """
    Вход в админ-панель.
    Показывает меню только для админов.
    """
    if not _is_admin(message.from_user.id, config):
        await message.answer("У вас нет доступа к админ-панели.")
        return

    await message.answer(
        "Админ-панель:",
        reply_markup=admin_main_keyboard(),
    )


# ======================
#   Заявки мастеров
# ======================

@router.callback_query(F.data == "admin:masters:pending")
async def admin_show_pending(
    callback: CallbackQuery,
    db_pool: Pool,
    config: Config,
):
    """
    Показать список заявок мастеров со статусом 'new'.
    """
    if not _is_admin(callback.from_user.id, config):
        await callback.answer("Нет доступа")
        return

    masters = await get_pending_masters(db_pool)
    if not masters:
        await callback.message.answer("Нет заявок мастеров.")
        await callback.answer()
        return

    for m in masters:
        text = (
            f"Заявка мастера #{m['id']}:\n\n"
            f"Имя: {m['name']}\n"
            f"Телефон: {m['phone']}\n"
            f"Username: @{m['username'] or '-'}\n"
            f"Категория: {m['category']}\n"
            f"Описание: {m['description']}\n"
            f"Цены: {m['price_min'] or ''}–{m['price_max'] or ''}\n"
        )
        if m["photo_file_id"]:
            await callback.message.answer_photo(
                photo=m["photo_file_id"],
                caption=text,
                reply_markup=admin_pending_master_keyboard(m["id"]),
            )
        else:
            await callback.message.answer(
                text,
                reply_markup=admin_pending_master_keyboard(m["id"]),
            )

    await callback.answer()


@router.callback_query(F.data.startswith("admin:masters:approve:"))
async def admin_approve_master(
    callback: CallbackQuery,
    db_pool: Pool,
    config: Config,
):
    """
    Одобрение заявки мастера.
    """
    if not _is_admin(callback.from_user.id, config):
        await callback.answer("Нет доступа")
        return

    try:
        _, _, _, master_id_str = callback.data.split(":", 3)
        master_id = int(master_id_str)
    except Exception:
        await callback.answer("Некорректные данные")
        return

    master = await get_master_by_id(db_pool, master_id)
    if not master:
        await callback.message.answer("Мастер не найден.")
        await callback.answer()
        return

    await set_master_status(db_pool, master_id, "approved")
    await callback.message.answer(f"Мастер #{master_id} одобрен.")
    await callback.answer()

    # Уведомим мастера
    if master["telegram_id"]:
        try:
            await callback.bot.send_message(
                master["telegram_id"],
                "Ваша заявка мастера одобрена! Вы теперь видны в каталоге.",
            )
        except Exception:
            # Могут быть ошибки, если пользователь запретил сообщения от бота и т.п.
            pass


@router.callback_query(F.data.startswith("admin:masters:reject:"))
async def admin_reject_master(
    callback: CallbackQuery,
    db_pool: Pool,
    config: Config,
):
    """
    Отклонение заявки мастера.
    """
    if not _is_admin(callback.from_user.id, config):
        await callback.answer("Нет доступа")
        return

    try:
        _, _, _, master_id_str = callback.data.split(":", 3)
        master_id = int(master_id_str)
    except Exception:
        await callback.answer("Некорректные данные")
        return

    master = await get_master_by_id(db_pool, master_id)
    if not master:
        await callback.message.answer("Мастер не найден.")
        await callback.answer()
        return

    await set_master_status(db_pool, master_id, "rejected")
    await callback.message.answer(f"Мастер #{master_id} отклонён.")
    await callback.answer()

    if master["telegram_id"]:
        try:
            await callback.bot.send_message(
                master["telegram_id"],
                "К сожалению, ваша заявка мастера была отклонена.",
            )
        except Exception:
            pass


@router.callback_query(F.data == "admin:masters:all")
async def admin_all_masters(
    callback: CallbackQuery,
    db_pool: Pool,
    config: Config,
):
    """
    Показ списка всех мастеров.
    """
    if not _is_admin(callback.from_user.id, config):
        await callback.answer("Нет доступа")
        return

    masters = await get_all_masters(db_pool)
    if not masters:
        await callback.message.answer("Мастеров пока нет.")
        await callback.answer()
        return

    lines: List[str] = ["Список всех мастеров:", ""]
    for m in masters:
        lines.append(
            f"#{m['id']} {m['name']} — статус: {m['status']}, "
            f"категория: {m['category']}, рейтинг: {m['rating']}"
        )

    await callback.message.answer("\n".join(lines))
    await callback.answer()


# ======================
#   Инфо-разделы
# ======================

@router.callback_query(F.data == "admin:info:menu")
async def admin_info_menu(
    callback: CallbackQuery,
    config: Config,
):
    """
    Меню управления инфо-разделами.
    """
    if not _is_admin(callback.from_user.id, config):
        await callback.answer("Нет доступа")
        return

    await callback.message.answer(
        "Управление инфо-разделами:",
        reply_markup=admin_info_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:info:edit:"))
async def admin_info_edit(
    callback: CallbackQuery,
    state: FSMContext,
    db_pool: Pool,
    config: Config,
):
    """
    Начало редактирования страницы "О нас" или "Контакты".
    """
    if not _is_admin(callback.from_user.id, config):
        await callback.answer("Нет доступа")
        return

    _, _, _, slug = callback.data.split(":", 3)

    page = await get_info_page(db_pool, slug)

    await state.clear()
    await state.update_data(slug=slug)

    if page:
        await callback.message.answer(
            f"Текущий текст страницы «{page['title']}»:\n\n{page['content']}\n\n"
            "Отправьте новый заголовок:"
        )
    else:
        await callback.message.answer(
            f"Страница с кодом «{slug}» ещё не создана.\n"
            "Отправьте заголовок страницы:"
        )

    await callback.answer()
    await state.set_state(InfoEditStates.title)


@router.message(InfoEditStates.title)
async def admin_info_edit_title(message: Message, state: FSMContext):
    """
    Получаем новый заголовок страницы.
    """
    await state.update_data(title=message.text.strip())
    await message.answer("Отправьте содержимое страницы:")
    await state.set_state(InfoEditStates.content)


@router.message(InfoEditStates.content)
async def admin_info_edit_content(
    message: Message,
    state: FSMContext,
    db_pool: Pool,
):
    """
    Сохраняем изменённую инфо-страницу.
    """
    data = await state.get_data()
    slug = data["slug"]
    title = data["title"]
    content = message.text.strip()

    await update_info_page(db_pool, slug=slug, title=title, content=content)
    await message.answer("Страница обновлена.")
    await state.clear()


# ======================
#   FAQ
# ======================

@router.callback_query(F.data == "admin:faq:menu")
async def admin_faq_menu(
    callback: CallbackQuery,
    config: Config,
):
    """
    Меню управления FAQ.
    """
    if not _is_admin(callback.from_user.id, config):
        await callback.answer("Нет доступа")
        return

    await callback.message.answer(
        "Управление FAQ:",
        reply_markup=admin_faq_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "admin:faq:add")
async def admin_faq_add_start(
    callback: CallbackQuery,
    state: FSMContext,
    config: Config,
):
    """
    Старт добавления FAQ.
    """
    if not _is_admin(callback.from_user.id, config):
        await callback.answer("Нет доступа")
        return

    await state.clear()
    await callback.message.answer("Отправьте текст вопроса:")
    await callback.answer()
    await state.set_state(FAQAddStates.question)


@router.message(FAQAddStates.question)
async def admin_faq_question(message: Message, state: FSMContext):
    """
    Получаем текст вопроса для FAQ.
    """
    await state.update_data(question=message.text.strip())
    await message.answer("Отправьте текст ответа:")
    await state.set_state(FAQAddStates.answer)


@router.message(FAQAddStates.answer)
async def admin_faq_answer(
    message: Message,
    state: FSMContext,
    db_pool: Pool,
):
    """
    Сохраняем новый вопрос-ответ в FAQ.
    """
    data = await state.get_data()
    question = data["question"]
    answer = message.text.strip()

    await add_faq(db_pool, question=question, answer=answer)
    await message.answer("FAQ добавлен.")
    await state.clear()
