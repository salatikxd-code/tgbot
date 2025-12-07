import asyncio
import logging
from datetime import datetime, timezone

from aiogram import Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    BotCommand,
    CallbackQuery
)

from app.bot.bot_instance import bot
from app.bot.scheduler import setup_scheduler, cancel_reminders

from app.db import (
    get_status,
    set_status,
    get_user_by_tg_id,
    get_all_receivers,
    add_user,
    init_db
)

from app.models import RoleEnum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
dp = Dispatcher()


# ---------------------------------------------------------
# КНОПКА "Отправить запрос администратору"
# ---------------------------------------------------------

def guest_request_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="📨 Отправить запрос администратору",
                callback_data="guest_request_access"
            )]
        ]
    )


# ---------------------------------------------------------
# Reply-клавиатура основная
# ---------------------------------------------------------

reply_kb = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Проверить статус"),
            KeyboardButton(text="Оборудование включено"),
            KeyboardButton(text="Оборудование выключено")
        ],
        [KeyboardButton(text="Админка")]
    ],
    resize_keyboard=True,
    is_persistent=True
)


# ---------------------------------------------------------
# Inline-кнопки статуса
# ---------------------------------------------------------

def status_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Оборудование включено", callback_data="set_on"),
                InlineKeyboardButton(text="Оборудование выключено", callback_data="set_off"),
            ]
        ]
    )


# ---------------------------------------------------------
# Проверка прав
# ---------------------------------------------------------

async def user_has_access(tg_id: int) -> bool:
    user = await asyncio.to_thread(get_user_by_tg_id, tg_id)
    return user and user.role.value in ["admin", "user", "notifier"]


def unauthorized_message():
    return ("⛔ У вас нет доступа.\n"
            "Нажмите кнопку ниже, чтобы отправить запрос администратору.")


# ---------------------------------------------------------
# Обработка запроса доступа
# ---------------------------------------------------------

@dp.callback_query(F.data == "guest_request_access")
async def guest_request_access(cb: CallbackQuery):

    user = await asyncio.to_thread(get_user_by_tg_id, cb.from_user.id)

    # отправляем админам запрос
    receivers = await asyncio.to_thread(get_all_receivers)

    for uid in receivers:
        try:
            await bot.send_message(
                uid,
                f"📨 <b>Новый запрос доступа!</b>\n"
                f"👤 Имя: {cb.from_user.first_name}\n"
                f"🆔 ID: {cb.from_user.id}",
                parse_mode="HTML"
            )
        except:
            pass

    await cb.answer("Запрос отправлен!", show_alert=True)


# ---------------------------------------------------------
# АДМИНКА
# ---------------------------------------------------------

@dp.message(lambda m: m.text and m.text.strip() == "Админка")
async def admin_link(msg: Message):
    user = await asyncio.to_thread(get_user_by_tg_id, msg.from_user.id)

    if not user or user.role != RoleEnum.admin:
        await msg.answer(
            unauthorized_message(),
            reply_markup=guest_request_keyboard()
        )
        return

    # Кликабельная ссылка
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔐 Открыть админку", url="http://localhost:8000/admin/")]
        ]
    )

    await msg.answer("Админ-панель:", reply_markup=kb)



# ---------------------------------------------------------
# Команда /start
# ---------------------------------------------------------

@dp.message(CommandStart())
async def start_cmd(msg: Message):
    tg_id = msg.from_user.id
    user = await asyncio.to_thread(get_user_by_tg_id, tg_id)

    if user is None:
        await asyncio.to_thread(
            add_user,
            tg_id,
            msg.from_user.first_name or str(tg_id),
            RoleEnum.guest
        )
        await msg.answer(
            "Вы зарегистрированы как гость. У вас нет доступа.",
            reply_markup=guest_request_keyboard()
        )

    st = await asyncio.to_thread(get_status)

    await msg.answer(
        f"Текущий статус оборудования: {'ВКЛ' if st.status == 'on' else 'ВЫКЛ'}",
        reply_markup=status_keyboard()
    )
    await msg.answer("Меню:", reply_markup=reply_kb)



# ---------------------------------------------------------
# Команды /status /on /off
# ---------------------------------------------------------

@dp.message(Command("status"))
async def status_cmd(msg: Message):
    st = await asyncio.to_thread(get_status)
    await msg.answer(f"Статус оборудования: {'ВКЛ' if st.status == 'on' else 'ВЫКЛ'}")


@dp.message(Command("on"))
async def cmd_on(msg: Message):

    if not await user_has_access(msg.from_user.id):
        await msg.answer(unauthorized_message(), reply_markup=guest_request_keyboard())
        return

    await asyncio.to_thread(set_status, "on", msg.from_user.id)
    cancel_reminders()

    await msg.answer("Статус оборудования: ВКЛЮЧЕНО")


@dp.message(Command("off"))
async def cmd_off(msg: Message):

    if not await user_has_access(msg.from_user.id):
        await msg.answer(unauthorized_message(), reply_markup=guest_request_keyboard())
        return

    await asyncio.to_thread(set_status, "off", msg.from_user.id)
    cancel_reminders()

    await msg.answer("Статус оборудования: ВЫКЛЮЧЕНО")

    actor = await asyncio.to_thread(get_user_by_tg_id, msg.from_user.id)
    name = actor.name or actor.tg_id

    receivers = await asyncio.to_thread(get_all_receivers)
    for uid in receivers:
        try:
            await bot.send_message(uid, f"⚠️ Оборудование выключено пользователем: {name}")
        except:
            pass



# ---------------------------------------------------------
# Inline — set_on
# ---------------------------------------------------------

@dp.callback_query(F.data == "set_on")
async def inline_on(query):

    if not await user_has_access(query.from_user.id):
        await query.message.answer(
            unauthorized_message(),
            reply_markup=guest_request_keyboard()
        )
        await query.answer()
        return

    await asyncio.to_thread(set_status, "on", query.from_user.id)
    cancel_reminders()

    await query.message.edit_text(
        "Статус оборудования: ВКЛЮЧЕНО",
        reply_markup=status_keyboard()
    )
    await query.answer("Готово.")


# ---------------------------------------------------------
# Inline — set_off
# ---------------------------------------------------------

@dp.callback_query(F.data == "set_off")
async def inline_off(query):

    if not await user_has_access(query.from_user.id):
        await query.message.answer(
            unauthorized_message(),
            reply_markup=guest_request_keyboard()
        )
        await query.answer()
        return

    await asyncio.to_thread(set_status, "off", query.from_user.id)
    cancel_reminders()

    await query.message.edit_text(
        "Статус оборудования: ВЫКЛЮЧЕНО",
        reply_markup=status_keyboard()
    )
    await query.answer("Готово.")

    actor = await asyncio.to_thread(get_user_by_tg_id, query.from_user.id)
    name = actor.name or actor.tg_id

    receivers = await asyncio.to_thread(get_all_receivers)
    for uid in receivers:
        try:
            await bot.send_message(uid, f"⚠️ Оборудование выключено пользователем: {name}")
        except:
            pass



# ---------------------------------------------------------
# Reply — Проверить статус
# ---------------------------------------------------------

@dp.message(F.text == "Проверить статус")
async def reply_status(msg: Message):
    st = await asyncio.to_thread(get_status)
    await msg.answer(
        f"Статус оборудования: {'ВКЛ' if st.status == 'on' else 'ВЫКЛ'}",
        reply_markup=status_keyboard()
    )


# ---------------------------------------------------------
# Reply — Выключить
# ---------------------------------------------------------

@dp.message(F.text == "Оборудование выключено")
async def reply_turn_off(msg: Message):

    if not await user_has_access(msg.from_user.id):
        await msg.answer(unauthorized_message(), reply_markup=guest_request_keyboard())
        return

    st = await asyncio.to_thread(get_status)
    if st.status == "off":
        await msg.answer("Оборудование уже выключено.")
        return

    await asyncio.to_thread(set_status, "off", msg.from_user.id)

    actor = await asyncio.to_thread(get_user_by_tg_id, msg.from_user.id)
    name = actor.name or actor.tg_id

    receivers = await asyncio.to_thread(get_all_receivers)
    for uid in receivers:
        try:
            await bot.send_message(uid, f"⚠️ Оборудование выключено пользователем: {name}")
        except:
            pass

    await msg.answer("Оборудование выключено!")


# ---------------------------------------------------------
# Reply — Включить
# ---------------------------------------------------------

@dp.message(F.text == "Оборудование включено")
async def reply_turn_on(msg: Message):

    if not await user_has_access(msg.from_user.id):
        await msg.answer(unauthorized_message(), reply_markup=guest_request_keyboard())
        return

    st = await asyncio.to_thread(get_status)
    if st.status == "on":
        await msg.answer("Оборудование уже включено.")
        return

    await asyncio.to_thread(set_status, "on", msg.from_user.id)
    await msg.answer("Оборудование включено!")


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

async def main():
    init_db()
    setup_scheduler()
    await bot.set_my_commands([
        BotCommand(command="start", description="Запуск бота"),
        BotCommand(command="status", description="Проверить статус"),
        BotCommand(command="on", description="Включить оборудование"),
        BotCommand(command="off", description="Выключить оборудование"),
    ])

    logger.info("Bot started...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
