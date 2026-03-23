import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

# ========== БЕРЕМ ДАННЫЕ ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ==========
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = os.environ.get("ADMIN_ID")
CHANNEL_ID = os.environ.get("CHANNEL_ID")

# Проверка наличия переменных
if not BOT_TOKEN:
    print("❌ ОШИБКА: BOT_TOKEN не задан в переменных окружения")
    exit(1)

if not ADMIN_ID:
    print("❌ ОШИБКА: ADMIN_ID не задан в переменных окружения")
    exit(1)

try:
    ADMIN_ID = int(ADMIN_ID)
except ValueError:
    print(f"❌ ОШИБКА: ADMIN_ID должен быть числом, получено: {ADMIN_ID}")
    exit(1)

# CHANNEL_ID опционален (может быть None)
if CHANNEL_ID:
    try:
        CHANNEL_ID = int(CHANNEL_ID)
    except ValueError:
        print(f"❌ ОШИБКА: CHANNEL_ID должен быть числом, получено: {CHANNEL_ID}")
        exit(1)
# ==========================================================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

waiting_for_reply = {}

def admin_keyboard(user_id):
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("✍️ Ответить", callback_data=f"reply_{user_id}"),
        InlineKeyboardButton("❌ Закрыть", callback_data=f"close_{user_id}")
    )
    return keyboard

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer(
        "👋 Привет! Я бот поддержки.\n\n"
        "Просто отправь мне сообщение, и я передам его оператору.\n"
        "Ответ придет сюда же."
    )

@dp.message_handler(commands=['admin'])
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Нет доступа")
        return
    
    status = f"📊 *Статус бота*\n\n"
    status += f"✅ Бот работает\n"
    status += f"👨‍💼 Админ: {ADMIN_ID}\n"
    if CHANNEL_ID:
        status += f"📢 Канал: {CHANNEL_ID}\n"
    else:
        status += f"📢 Канал: не настроен\n"
    status += f"💬 Активных диалогов: {len(waiting_for_reply)}"
    
    await message.answer(status, parse_mode="Markdown")

@dp.message_handler(commands=['post'])
async def send_post_button(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Нет доступа")
        return
    
    if not CHANNEL_ID:
        await message.answer("❌ Канал не настроен. Добавьте CHANNEL_ID в переменные окружения.")
        return
    
    keyboard = InlineKeyboardMarkup(row_width=1)
    me = await bot.get_me()
    keyboard.add(
        InlineKeyboardButton(
            "📩 Написать в поддержку", 
            url=f"https://t.me/{me.username}"
        )
    )
    
    try:
        await bot.send_message(
            CHANNEL_ID,
            "❓ *Есть вопросы или проблемы?*\n\n"
            "Нажмите на кнопку ниже, чтобы связаться с поддержкой.\n"
            "Мы ответим в ближайшее время!",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        await message.answer("✅ Кнопка отправлена в канал!")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}\n\nУбедитесь, что бот добавлен в админы канала.")

@dp.message_handler(content_types=['text', 'photo', 'video', 'document', 'voice'])
async def handle_message(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        return
    
    user = message.from_user
    msg_text = f"📩 *Новое сообщение*\n👤 {user.full_name}\n🆔 @{user.username if user.username else 'нет'}\n📱 ID: `{user.id}`\n\n"
    
    await message.answer("✅ Сообщение отправлено в поддержку! Ответ придет сюда.")
    
    try:
        if message.text:
            await bot.send_message(
                ADMIN_ID, 
                msg_text + message.text, 
                parse_mode="Markdown",
                reply_markup=admin_keyboard(user.id)
            )
        elif message.photo:
            await bot.send_photo(
                ADMIN_ID, 
                message.photo[-1].file_id, 
                caption=msg_text, 
                parse_mode="Markdown",
                reply_markup=admin_keyboard(user.id)
            )
        elif message.video:
            await bot.send_video(
                ADMIN_ID, 
                message.video.file_id, 
                caption=msg_text, 
                parse_mode="Markdown",
                reply_markup=admin_keyboard(user.id)
            )
        elif message.document:
            await bot.send_document(
                ADMIN_ID, 
                message.document.file_id, 
                caption=msg_text, 
                parse_mode="Markdown",
                reply_markup=admin_keyboard(user.id)
            )
        elif message.voice:
            await bot.send_voice(
                ADMIN_ID, 
                message.voice.file_id, 
                caption=msg_text, 
                parse_mode="Markdown",
                reply_markup=admin_keyboard(user.id)
            )
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await message.answer("❌ Ошибка отправки. Попробуйте позже.")

@dp.callback_query_handler(lambda c: c.data.startswith('reply_'))
async def reply_callback(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    user_id = int(callback.data.split('_')[1])
    waiting_for_reply[ADMIN_ID] = user_id
    await callback.message.answer(f"✍️ Введите ответ для пользователя {user_id}:")
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith('close_'))
async def close_callback(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    user_id = int(callback.data.split('_')[1])
    try:
        await bot.send_message(user_id, "🛑 Диалог закрыт. Если остались вопросы, напишите новое сообщение.")
    except:
        pass
    
    if user_id in waiting_for_reply:
        del waiting_for_reply[user_id]
    
    await callback.message.answer(f"✅ Диалог с пользователем {user_id} закрыт")
    await callback.answer()

@dp.message_handler(lambda m: m.from_user.id == ADMIN_ID and ADMIN_ID in waiting_for_reply)
async def send_reply(message: types.Message):
    user_id = waiting_for_reply.pop(ADMIN_ID, None)
    if not user_id:
        return
    
    try:
        if message.text:
            await bot.send_message(
                user_id, 
                f"📨 *Ответ поддержки:*\n\n{message.text}", 
                parse_mode="Markdown"
            )
        elif message.photo:
            await bot.send_photo(
                user_id, 
                message.photo[-1].file_id, 
                caption="📨 *Ответ поддержки:*", 
                parse_mode="Markdown"
            )
        elif message.video:
            await bot.send_video(
                user_id, 
                message.video.file_id, 
                caption="📨 *Ответ поддержки:*", 
                parse_mode="Markdown"
            )
        else:
            await bot.send_message(
                user_id, 
                "📨 *Ответ поддержки:*\n\n(файл получен)", 
                parse_mode="Markdown"
            )
        
        await message.answer(f"✅ Ответ отправлен пользователю {user_id}")
        
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(InlineKeyboardButton("✅ Закрыть диалог", callback_data=f"close_{user_id}"))
        await message.answer("Диалог завершен? Нажмите кнопку, чтобы закрыть:", reply_markup=kb)
        
    except Exception as e:
        await message.answer(f"❌ Ошибка отправки: {e}")

if __name__ == '__main__':
    print("🤖 Бот поддержки запущен!")
    print(f"👨‍💼 Админ: {ADMIN_ID}")
    if CHANNEL_ID:
        print(f"📢 Канал: {CHANNEL_ID}")
    else:
        print("📢 Канал: не настроен")
    executor.start_polling(dp, skip_updates=True)
