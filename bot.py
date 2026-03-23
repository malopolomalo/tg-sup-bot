import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
import os

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
# =================================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# Хранилище
waiting_for_reply = {}

def admin_keyboard(user_id):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("✍️ Ответить", callback_data=f"reply_{user_id}"))
    keyboard.add(InlineKeyboardButton("❌ Закрыть", callback_data=f"close_{user_id}"))
    return keyboard

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("👋 Привет! Отправь сообщение, я передам админу.")

@dp.message_handler(content_types=['text', 'photo', 'video', 'document', 'voice'])
async def handle_message(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        return
    
    user = message.from_user
    user_text = f"📩 От: {user.full_name} (@{user.username})\nID: {user.id}\n\n"
    
    await message.answer("✅ Отправлено!")
    
    try:
        if message.text:
            await bot.send_message(
                ADMIN_ID,
                user_text + message.text,
                reply_markup=admin_keyboard(user.id)
            )
        elif message.photo:
            await bot.send_photo(
                ADMIN_ID,
                message.photo[-1].file_id,
                caption=user_text,
                reply_markup=admin_keyboard(user.id)
            )
        elif message.video:
            await bot.send_video(
                ADMIN_ID,
                message.video.file_id,
                caption=user_text,
                reply_markup=admin_keyboard(user.id)
            )
        elif message.document:
            await bot.send_document(
                ADMIN_ID,
                message.document.file_id,
                caption=user_text,
                reply_markup=admin_keyboard(user.id)
            )
        elif message.voice:
            await bot.send_voice(
                ADMIN_ID,
                message.voice.file_id,
                caption=user_text,
                reply_markup=admin_keyboard(user.id)
            )
    except Exception as e:
        print(f"Ошибка: {e}")

@dp.callback_query_handler(lambda c: c.data.startswith('reply_'))
async def reply_callback(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    user_id = int(callback.data.split('_')[1])
    waiting_for_reply[ADMIN_ID] = user_id
    
    await callback.message.answer(f"✍️ Введите ответ для пользователя {user_id}:")
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith('close_'))
async def close_callback(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    user_id = int(callback.data.split('_')[1])
    
    try:
        await bot.send_message(user_id, "🛑 Диалог закрыт. Новые вопросы пишите сюда.")
    except:
        pass
    
    await callback.message.answer(f"✅ Диалог с {user_id} закрыт")
    await callback.answer()

@dp.message_handler(lambda m: m.from_user.id == ADMIN_ID and ADMIN_ID in waiting_for_reply)
async def send_reply(message: types.Message):
    user_id = waiting_for_reply.pop(ADMIN_ID, None)
    
    if not user_id:
        return
    
    try:
        if message.text:
            await bot.send_message(user_id, f"📨 *Ответ:*\n{message.text}", parse_mode="Markdown")
        elif message.photo:
            await bot.send_photo(user_id, message.photo[-1].file_id, caption="📨 *Ответ:*", parse_mode="Markdown")
        elif message.video:
            await bot.send_video(user_id, message.video.file_id, caption="📨 *Ответ:*", parse_mode="Markdown")
        else:
            await bot.send_message(user_id, "📨 *Ответ:* (файл получен)", parse_mode="Markdown")
        
        await message.answer(f"✅ Отправлено пользователю {user_id}")
        
        # Кнопка закрытия
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("✅ Закрыть", callback_data=f"close_{user_id}"))
        await message.answer("Закрыть диалог?", reply_markup=kb)
        
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
