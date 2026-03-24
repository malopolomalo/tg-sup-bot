import logging
import os
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
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

waiting_for_reply = {}

def admin_keyboard(user_id):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("✍️ Ответить", callback_data=f"reply_{user_id}"),
        InlineKeyboardButton("❌ Закрыть", callback_data=f"close_{user_id}")
    )
    return kb

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer(
        "👋 Бот поддержки.\n\n"
        "Отправь сообщение, я передам админу."
    )

@dp.message_handler(commands=['test'])
async def test(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    user_id = waiting_for_reply.get(ADMIN_ID, "никого")
    await message.answer(f"Сейчас ожидаю ответ для: {user_id}")

@dp.message_handler(commands=['send'])
async def send_to_user(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Используй: /send user_id текст")
        return
    try:
        user_id = int(parts[1])
        text = parts[2]
        await bot.send_message(user_id, f"📨 {text}")
        await message.answer(f"✅ Отправлено пользователю {user_id}")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

@dp.message_handler(commands=['post'])
async def send_post_button(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    if not CHANNEL_ID:
        await message.answer("❌ CHANNEL_ID не задан")
        return
    
    me = await bot.get_me()
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("📩 Написать в поддержку", url=f"https://t.me/{me.username}"))
    
    try:
        await bot.send_message(
            CHANNEL_ID,
            "❓ *Есть вопросы?*\n\nНажми на кнопку, чтобы написать в поддержку.",
            parse_mode="Markdown",
            reply_markup=kb
        )
        await message.answer("✅ Кнопка отправлена в канал!")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

@dp.message_handler(content_types=['text', 'photo', 'video', 'document', 'voice'])
async def handle_user(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        return
    
    user = message.from_user
    text = f"📩 От: {user.full_name}\nID: {user.id}\n\n"
    
    await message.answer("✅ Отправлено!")
    
    if message.text:
        await bot.send_message(ADMIN_ID, text + message.text, reply_markup=admin_keyboard(user.id))
    elif message.photo:
        await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=text, reply_markup=admin_keyboard(user.id))
    elif message.video:
        await bot.send_video(ADMIN_ID, message.video.file_id, caption=text, reply_markup=admin_keyboard(user.id))
    elif message.document:
        await bot.send_document(ADMIN_ID, message.document.file_id, caption=text, reply_markup=admin_keyboard(user.id))
    elif message.voice:
        await bot.send_voice(ADMIN_ID, message.voice.file_id, caption=text, reply_markup=admin_keyboard(user.id))

@dp.callback_query_handler(lambda c: c.data.startswith('reply_'))
async def reply_start(callback: types.CallbackQuery):
    print(f"🔍 Нажата кнопка reply: {callback.data}")
    
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    user_id = int(callback.data.split('_')[1])
    waiting_for_reply[ADMIN_ID] = user_id
    
    print(f"✅ Сохранено: waiting_for_reply[{ADMIN_ID}] = {user_id}")
    
    await callback.message.answer(f"✍️ Введите ответ для пользователя {user_id}:")
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith('close_'))
async def close_dialog(callback: types.CallbackQuery):
    print(f"🔍 Нажата кнопка close: {callback.data}")
    
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    user_id = int(callback.data.split('_')[1])
    
    if ADMIN_ID in waiting_for_reply and waiting_for_reply[ADMIN_ID] == user_id:
        del waiting_for_reply[ADMIN_ID]
    
    try:
        await bot.send_message(user_id, "🛑 Диалог закрыт.")
    except:
        pass
    
    await callback.message.answer(f"✅ Диалог с {user_id} закрыт")
    await callback.answer()

@dp.message_handler(lambda m: m.from_user.id == ADMIN_ID)
async def handle_admin_message(message: types.Message):
    user_id = waiting_for_reply.pop(ADMIN_ID, None)
    
    if not user_id:
        # Если нет ожидающего ответа, проверяем может это команда
        if message.text and message.text.startswith('/'):
            return
        return
    
    try:
        if message.text:
            await bot.send_message(user_id, f"📨 *Ответ:*\n{message.text}", parse_mode="Markdown")
        elif message.photo:
            await bot.send_photo(user_id, message.photo[-1].file_id, caption="📨 *Ответ:*", parse_mode="Markdown")
        elif message.video:
            await bot.send_video(user_id, message.video.file_id, caption="📨 *Ответ:*", parse_mode="Markdown")
        elif message.document:
            await bot.send_document(user_id, message.document.file_id, caption="📨 *Ответ:*", parse_mode="Markdown")
        elif message.voice:
            await bot.send_voice(user_id, message.voice.file_id)
        else:
            await bot.send_message(user_id, "📨 *Ответ:*", parse_mode="Markdown")
        
        await message.answer(f"✅ Отправлено пользователю {user_id}")
        
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(InlineKeyboardButton("✅ Закрыть", callback_data=f"close_{user_id}"))
        await message.answer("Закрыть диалог?", reply_markup=kb)
        
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

if __name__ == '__main__':
    print("🤖 Бот запущен!")
    executor.start_polling(dp, skip_updates=True)
