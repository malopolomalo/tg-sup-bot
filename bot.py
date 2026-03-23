import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
import os

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Берем из переменных окружения
ADMIN_ID = int(os.getenv("ADMIN_ID"))  # Берем из переменных окружения
CHANNEL_ID = os.getenv("CHANNEL_ID", None)  # Если не указан, будет None
if CHANNEL_ID and CHANNEL_ID != "None":
    CHANNEL_ID = int(CHANNEL_ID)
else:
    CHANNEL_ID = None
# =================================

logging.basicConfig(level=logging.INFO)
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)

active_dialogs = {}

class ReplyState(StatesGroup):
    waiting_for_reply = State()

def admin_keyboard(user_id, msg_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✍️ Ответить", callback_data=f"reply_{user_id}_{msg_id}")],
        [InlineKeyboardButton(text="❌ Закрыть диалог", callback_data=f"close_{user_id}")]
    ])

def close_keyboard(user_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Закрыть диалог", callback_data=f"close_{user_id}")]
    ])

@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer(
        "👋 Привет! Я бот поддержки.\n\n"
        "Просто отправь мне сообщение, и я передам его админу.\n"
        "Ответ придет сюда же."
    )

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ У вас нет доступа к этой команде")
        return
    
    active_count = len(active_dialogs)
    await message.answer(
        f"📊 *Админ-панель*\n\n"
        f"Активных диалогов: {active_count}\n\n"
        f"Бот работает 24/7",
        parse_mode="Markdown"
    )

@dp.message(F.text | F.photo | F.video | F.document | F.voice)
async def handle_user_message(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        return
    
    user = message.from_user
    user_info = f"👤 {user.full_name}\n🆔 @{user.username if user.username else 'нет'}\n📱 ID: {user.id}"
    
    if user.id not in active_dialogs:
        active_dialogs[user.id] = {
            'first_msg': datetime.now(),
            'last_msg': datetime.now(),
            'user_name': user.full_name
        }
    else:
        active_dialogs[user.id]['last_msg'] = datetime.now()
    
    await message.answer("✅ Сообщение отправлено в поддержку. Ответ придет сюда.")
    
    try:
        if message.text:
            await bot.send_message(
                ADMIN_ID,
                f"📩 *Новое сообщение*\n{user_info}\n\n{message.text}",
                parse_mode="Markdown",
                reply_markup=admin_keyboard(user.id, message.message_id)
            )
        elif message.photo:
            caption = f"📸 *Фото от пользователя*\n{user_info}"
            await bot.send_photo(
                ADMIN_ID,
                message.photo[-1].file_id,
                caption=caption,
                parse_mode="Markdown",
                reply_markup=admin_keyboard(user.id, message.message_id)
            )
        elif message.video:
            caption = f"🎥 *Видео от пользователя*\n{user_info}"
            await bot.send_video(
                ADMIN_ID,
                message.video.file_id,
                caption=caption,
                parse_mode="Markdown",
                reply_markup=admin_keyboard(user.id, message.message_id)
            )
        elif message.document:
            caption = f"📄 *Документ от пользователя*\n{user_info}"
            await bot.send_document(
                ADMIN_ID,
                message.document.file_id,
                caption=caption,
                parse_mode="Markdown",
                reply_markup=admin_keyboard(user.id, message.message_id)
            )
        elif message.voice:
            caption = f"🎤 *Голосовое от пользователя*\n{user_info}"
            await bot.send_voice(
                ADMIN_ID,
                message.voice.file_id,
                caption=caption,
                parse_mode="Markdown",
                reply_markup=admin_keyboard(user.id, message.message_id)
            )
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await message.answer("❌ Ошибка отправки. Попробуйте позже.")

@dp.callback_query(F.data.startswith("reply_"))
async def start_reply(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Только админ может отвечать", show_alert=True)
        return
    
    _, user_id, msg_id = callback.data.split("_")
    user_id = int(user_id)
    
    await state.update_data(reply_to=user_id)
    await state.set_state(ReplyState.waiting_for_reply)
    
    await callback.message.answer(
        f"✍️ Введите ответ для пользователя {user_id}\n"
        f"Можно отправить текст, фото, видео или файл"
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("close_"))
async def close_dialog(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Только админ", show_alert=True)
        return
    
    _, user_id = callback.data.split("_")
    user_id = int(user_id)
    
    if user_id in active_dialogs:
        del active_dialogs[user_id]
    
    try:
        await bot.send_message(
            user_id,
            "🛑 Диалог закрыт. Если остались вопросы, напишите новое сообщение."
        )
    except:
        pass
    
    await callback.message.answer(f"✅ Диалог с пользователем {user_id} закрыт")
    await callback.answer()

@dp.message(ReplyState.waiting_for_reply)
async def send_reply(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Вы не админ")
        await state.clear()
        return
    
    data = await state.get_data()
    user_id = data.get("reply_to")
    
    if not user_id:
        await message.answer("❌ Ошибка: пользователь не найден")
        await state.clear()
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
        elif message.document:
            await bot.send_document(
                user_id,
                message.document.file_id,
                caption="📨 *Ответ поддержки:*",
                parse_mode="Markdown"
            )
        elif message.voice:
            await bot.send_voice(
                user_id,
                message.voice.file_id,
                caption="📨 *Ответ поддержки:*",
                parse_mode="Markdown"
            )
        
        await message.answer(f"✅ Ответ отправлен пользователю {user_id}")
        await message.answer(
            "Диалог завершен? Нажмите кнопку, чтобы закрыть обращение:",
            reply_markup=close_keyboard(user_id)
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка отправки: {e}")
    
    await state.clear()

async def main():
    print("🤖 Бот поддержки запущен!")
    print(f"👨‍💼 Админ: {ADMIN_ID}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())