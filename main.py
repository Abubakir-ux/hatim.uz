import asyncio
import logging
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, BotCommand
from aiogram.exceptions import TelegramBadRequest
from aiogram.client.default import DefaultBotProperties

API_TOKEN = '8655041954:AAHs4kQitwIu0hnOblkyd9NM3bQSHPDoYO8'

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()

xatm_db = {}


def make_text(data):
    lines = ["📖 <b>Xatim yaratildi!</b>", ""]
    lines.append(f"👤 Yaratuvchi: {data['creator_username']}")
    lines.append("")
    if data["users"]:
        lines.append("📋 Qatnashuvchilar:")
        for i, name in enumerate(data["users"].values(), 1):
            lines.append(f"{i}. {name}")
    else:
        lines.append("📋 Qatnashuvchilar: hali yo'q")
    return "\n".join(lines)


def taqsimla(users, jami=30):
    n = len(users)
    names = list(users.values())
    ulushlar = [1] * n
    for _ in range(jami - n):
        ulushlar[random.randint(0, n - 1)] += 1
    return list(zip(names, ulushlar))


def get_others(data):
    return [uid for uid in data["users"] if uid != data["creator_id"]]


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.chat.type != "private":
        return
    bot_info = await bot.get_me()
    text = (
        "🕌 <b>Xatim.uz Botiga Xush Kelibsiz!</b>\n\n"
        "Bu bot guruhda <b>Xatim</b> tashkil qilishga yordam beradi.\n\n"
        "📌 <b>Qanday ishlaydi?</b>\n\n"
        "1️⃣ Botni guruhingizga qo'shing\n"
        "2️⃣ Guruhda <code>/xatimyaratish</code> buyrug'ini yozing\n"
        "3️⃣ Qatnashchilar <b>Qo'shilish</b> tugmasini bosadi\n"
        "4️⃣ Siz <b>Boshlash</b> tugmasini bosasiz\n"
        "5️⃣ Bot avtomatik <b>30 juzni</b> taqsimlaydi 📖\n\n"
        "👇 Botni guruhga qo'shish:"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="➕ Guruhga qo'shish", url=f"https://t.me/{bot_info.username}?startgroup=true")
    ]])
    await message.answer(text, reply_markup=kb)


@dp.message(Command("xatimyaratish"))
async def cmd_xatim(message: types.Message):
    user = message.from_user
    if not user:
        return

    creator_id = user.id
    creator_username = f"@{user.username}" if user.username else user.full_name

    data = {
        "creator_id": creator_id,
        "creator_username": creator_username,
        "users": {creator_id: creator_username},
        "chat_id": message.chat.id,
    }

    sent = await message.answer(make_text(data))
    xatm_db[sent.message_id] = data

    await sent.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="➕ Qo'shilish", callback_data=f"join_{sent.message_id}")
    ]]))


@dp.callback_query(F.data.startswith("join_"))
async def cb_join(callback: CallbackQuery):
    msg_id = int(callback.data.split("_")[1])
    if msg_id not in xatm_db:
        return await callback.answer("Xatim topilmadi!", show_alert=True)

    data = xatm_db[msg_id]
    user_id = callback.from_user.id
    username = f"@{callback.from_user.username}" if callback.from_user.username else callback.from_user.full_name

    if user_id == data["creator_id"]:
        return await callback.answer()

    if user_id in data["users"]:
        return await callback.answer("Allaqachon ro'yxatdasiz!", show_alert=False)

    data["users"][user_id] = username
    await callback.answer("Qo'shildingiz ✅")

    try:
        await callback.message.edit_text(
            make_text(data),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="⛔ Chiqish", callback_data=f"leave_{msg_id}")
            ]])
        )
    except TelegramBadRequest:
        pass


@dp.callback_query(F.data.startswith("leave_"))
async def cb_leave(callback: CallbackQuery):
    msg_id = int(callback.data.split("_")[1])
    if msg_id not in xatm_db:
        return await callback.answer("Xatim topilmadi!", show_alert=True)

    data = xatm_db[msg_id]
    user_id = callback.from_user.id

    # ADMIN bosdi — xatimni boshlash
    if user_id == data["creator_id"]:
        others = get_others(data)
        if len(others) == 0:
            return await callback.answer("Hali hech kim qo'shilmagan!", show_alert=True)
        taqsimlangan = taqsimla(data["users"], jami=30)
        lines = ["🕌 <b>Xatim boshlandi!</b>", ""]
        lines.append(f"Jami: {len(taqsimlangan)} kishi | 30 juz\n")
        for name, ulush in taqsimlangan:
            lines.append(f"• {name} — <b>{ulush} ta</b>")
        try:
            await callback.message.edit_text("\n".join(lines), reply_markup=None)
        except TelegramBadRequest:
            pass
        xatm_db.pop(msg_id, None)
        return await callback.answer("Boshlandi! 📖")

    # ODDIY ODAM — chiqish
    if user_id not in data["users"]:
        return await callback.answer("Siz ro'yxatda yo'qsiz!", show_alert=False)

    del data["users"][user_id]
    await callback.answer("Chiqdingiz ⛔")

    try:
        await callback.message.edit_text(
            make_text(data),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="➕ Qo'shilish", callback_data=f"join_{msg_id}")
            ]])
        )
    except TelegramBadRequest:
        pass


async def main():
    await bot.set_my_commands([
        BotCommand(command="start", description="Botni ishga tushirish"),
        BotCommand(command="xatimyaratish", description="Yangi xatim yaratish"),
    ])
    print("✅ Bot ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
