from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging
from config import API_TOKEN, ADMIN_ID, MEDIA_CHANNEL_ID
from utils import *
import re
import json
import os

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)

DATA_FILE = "videos.json"
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)

def load_data():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    save_user(user_id)

    if not await check_subscriptions(bot, user_id):
        sponsors = load_sponsors()
        keyboard = InlineKeyboardMarkup(row_width=1)

        for ch in sponsors:
            username = ch.strip('@')
            btn = InlineKeyboardButton(text=f"➕ {username}", url=f"https://t.me/{username}")
            keyboard.add(btn)

        keyboard.add(InlineKeyboardButton("✅ Obuna bo‘ldim", callback_data="check_subs"))

        await message.answer(
            "📛 Botdan foydalanish uchun quyidagi kanallarga obuna bo‘ling:",
            reply_markup=keyboard
        )
        return

    await message.answer("🎬 Qaysi film kerak? Raqam yuboring (masalan: 12)")

@dp.callback_query_handler(lambda c: c.data == "check_subs")
async def check_callback(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    if await check_subscriptions(bot, user_id):
        await bot.answer_callback_query(callback_query.id, "✅ Obuna tasdiqlandi!")
        await bot.send_message(user_id, "🎬 Endi raqam yuboring (masalan: 12), filmni jo‘nataman.")
    else:
        await bot.answer_callback_query(callback_query.id, "🚫 Obuna hali to‘liq emas!", show_alert=True)

@dp.message_handler(lambda msg: msg.text.isdigit())
async def send_video(message: types.Message):
    user_id = message.from_user.id

    if not await check_subscriptions(bot, user_id):
        sponsors = load_sponsors()
        keyboard = InlineKeyboardMarkup(row_width=1)

        for ch in sponsors:
            username = ch.strip('@')
            btn = InlineKeyboardButton(text=f"➕ {username}", url=f"https://t.me/{username}")
            keyboard.add(btn)

        keyboard.add(InlineKeyboardButton("✅ Obuna bo‘ldim", callback_data="check_subs"))

        await message.answer(
            "📛 Filmni olishdan oldin quyidagi kanallarga obuna bo‘ling:",
            reply_markup=keyboard
        )
        return

    msg_id = message.text.strip()
    data = load_data()

    if msg_id not in data:
        await message.reply("❌ Bu raqamga mos film topilmadi.")
        return

    try:
        post = await bot.copy_message(
            chat_id=message.chat.id,
            from_chat_id=MEDIA_CHANNEL_ID,
            message_id=data[msg_id]
        )
        await bot.edit_message_caption(
            chat_id=message.chat.id,
            message_id=post.message_id,
            caption="🎬 Filmni bot orqali oldingiz: @TopKinoBot"
        )
    except Exception as e:
        await message.reply("❌ Video yuborishda xatolik yuz berdi.")

# Kanalga video joylanganda izohdagi raqam asosida saqlash
@dp.message_handler(content_types=types.ContentType.VIDEO)
async def save_video(message: types.Message):
    if message.forward_from_chat and message.forward_from_message_id:
        if message.forward_from_chat.id == MEDIA_CHANNEL_ID:
            caption = message.caption or ""
            numbers = [word for word in caption.split() if word.isdigit()]
            if numbers:
                number = numbers[0]
                data = load_data()
                data[number] = message.forward_from_message_id
                save_data(data)
                await message.reply(f"✅ {number}-raqamli video saqlandi.")
            else:
                await message.reply("⚠️ Izohda raqam topilmadi.")
        else:
            await message.reply("⚠️ Videoni noto‘g‘ri kanaldan forward qildingiz.")
    elif message.forward_from_chat:
        await message.reply(f"📢 Kanal ID: `{message.forward_from_chat.id}`", parse_mode="Markdown")
    else:
        await message.reply("⚠️ Videoni forward qiling. Yuklab emas!")

# --- ADMIN BUYRUKLAR ---

@dp.message_handler(commands=['homiy_qosh'])
async def add_sponsor(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    text = message.text.split()
    if len(text) < 2:
        await message.reply("❗ Foydalanish: /homiy_qosh @kanal_username")
        return
    sponsor = text[1]
    sponsors = load_sponsors()
    if sponsor not in sponsors:
        sponsors.append(sponsor)
        save_sponsors(sponsors)
        await message.reply("✅ Homiy kanal qo‘shildi.")
    else:
        await message.reply("🔁 Bu kanal ro‘yxatda bor.")

@dp.message_handler(commands=['homiy_olib_tashla'])
async def remove_sponsor(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    text = message.text.split()
    if len(text) < 2:
        await message.reply("❗ Foydalanish: /homiy_olib_tashla @kanal_username")
        return
    sponsor = text[1]
    sponsors = load_sponsors()
    if sponsor in sponsors:
        sponsors.remove(sponsor)
        save_sponsors(sponsors)
        await message.reply("🗑 Homiy kanal o‘chirildi.")
    else:
        await message.reply("❌ Bunday kanal topilmadi.")

@dp.message_handler(commands=['homiylar'])
async def list_sponsors(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    sponsors = load_sponsors()
    if sponsors:
        await message.reply("📋 Homiylar ro‘yxati:\n" + "\n".join(sponsors))
    else:
        await message.reply("🚫 Hech qanday homiy kanal yo‘q.")

@dp.message_handler(commands=['xabar_yubor'])
async def broadcast(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    text = message.text.replace("/xabar_yubor", "").strip()
    if not text:
        await message.reply("✉️ Xabar yuborish uchun matn kiriting:\n/xabar_yubor Salom!")
        return
    users = load_users()
    sent = 0
    for uid in users:
        try:
            await bot.send_message(uid, text)
            sent += 1
        except:
            continue
    await message.reply(f"📬 {sent} ta foydalanuvchiga xabar yuborildi.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
