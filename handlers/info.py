import asyncpg

from aiogram import Router, F
from aiogram.types import Message

from services.info_service import get_info_page, get_faq

router = Router()


@router.message(F.text == "О нас")
async def info_about(message: Message, db_pool: asyncpg.Pool):
    page = await get_info_page(db_pool, "about")
    if not page:
        await message.answer("Информация о нас пока не заполнена.")
        return

    await message.answer(
        f"<b>{page['title']}</b>\n\n{page['content']}"
    )


@router.message(F.text == "Контакты")
async def info_contacts(message: Message, db_pool: asyncpg.Pool):
    page = await get_info_page(db_pool, "contacts")
    if not page:
        await message.answer("Контакты пока не заполнены.")
        return

    await message.answer(
        f"<b>{page['title']}</b>\n\n{page['content']}"
    )


@router.message(F.text == "FAQ")
async def info_faq(message: Message, db_pool: asyncpg.Pool):
    faq = await get_faq(db_pool)
    if not faq:
        await message.answer("FAQ пока пустой.")
        return

    lines = ["<b>Частые вопросы</b>", ""]
    for item in faq:
        lines.append(f"❓ <b>{item['question']}</b>")
        lines.append(f"💬 {item['answer']}\n")

    await message.answer("\n".join(lines))
