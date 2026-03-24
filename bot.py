import logging
import os
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

# ========== HTTP-сервер для Render ==========
flask_app = Flask(__name__)

@flask_app.route('/')
def health():
    return "Bot is running!"

def run_http():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host='0.0.0.0', port=port)

Thread(target=run_http).start()
# ===========================================

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID"))
CHANNEL_ID = os.environ.get("CHANNEL_ID")
if CHANNEL_ID:
    CHANNEL_ID = int(CHANNEL_ID)

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# Храним последнего пользователя
last_user = {}

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer(
        "👋 Бот поддержки.\n\n"
        "Отправь сообщение, я передам админу.\n\n"
        "Админ ответит командой:\n"
        "/send текст — последнему, кто писал\n"
        "/send 123456789 текст — конкретному пользователю"
    )

@dp.message_handler(commands=['post'])
async def send_post_button(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    if not CHANNEL_ID:
        await message.answer("❌ CHANNEL_ID не задан")
        return
    
    me = await bot.get_me()
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📩 Написать в поддержку", url=f"https://t.me/{me.username}"))
    
    try:
        await bot.send_message(
            CHANNEL_ID,
            "❓ *Есть вопросы?*\n\nНажми на кнопку, чтобы написать в поддержку.",
            parse_mode="Markdown",
            reply_markup=kb
        )
        await message.answer("✅ Отправлено!")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

@dp.message_handler(content_types=['text', 'photo', 'video', 'document', 'voice'])
async def handle_user(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        return
    
    user = message.from_user
    last_user[ADMIN_ID] = user.id
    
    user_text = f"📩 От: {user.full_name}\nID: {user.id}\n\n"
    
    await message.answer("✅ Отправлено!")
    
    if message.text:
        await bot.send_message(ADMIN_ID, user_text + message.text)
    elif message.photo:
        await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=user_text)
    elif message.video:
        await bot.send_video(ADMIN_ID, message.video.file_id, caption=user_text)
    elif message.document:
        await bot.send_document(ADMIN_ID, message.document.file_id, caption=user_text)
    elif message.voice:
        await bot.send_voice(ADMIN_ID, message.voice.file_id, caption=user_text)
    
    await bot.send_message(
        ADMIN_ID,
        f"💡 Чтобы ответить:\n/send {user.id} текст\nили\n/send текст (ответит последнему)"
    )

@dp.message_handler(commands=['send'])
async def send_command(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    parts = message.text.split(maxsplit=2)
    
    # /send текст
    if len(parts) == 2:
        user_id = last_user.get(ADMIN_ID)
        text = parts[1]
        if not user_id:
            await message.answer("❌ Нет активного диалога. Используй: /send user_id текст")
            return
    
    # /send user_id текст
    elif len(parts) >= 3:
        try:
            user_id = int(parts[1])
            text = parts[2]
        except:
            await message.answer("❌ Ошибка. Используй: /send user_id текст")
            return
    else:
        await message.answer("❌ Используй:\n/send текст\nили\n/send 123456789 текст")
        return
    
    try:
        await bot.send_message(user_id, f"📨 *Ответ:*\n{text}", parse_mode="Markdown")
        await message.answer(f"✅ Отправлено пользователю {user_id}")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

if __name__ == '__main__':
    print("🤖 Бот запущен!")
    executor.start_polling(dp, skip_updates=True)
