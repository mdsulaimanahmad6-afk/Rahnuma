import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import Command

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = "@Rahnuma_e_Deen"
MINI_APP_URL = os.getenv("MINI_APP_URL", "https://your-app.onrender.com")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        if member.status in ["member", "administrator", "creator"]:
            await message.answer("✅ Aap already verified hain! Ab aap bot use kar sakte hain.")
            return
    except Exception as e:
        print(f"Error checking member: {e}")

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Channel Join Karein", url="https://t.me/Rahnuma_e_Deen")],
        [InlineKeyboardButton(text="🛡️ Verify Now", web_app=WebAppInfo(url=MINI_APP_URL))]
    ])
    await message.answer("⚠️ Verification ke liye pehle in channels ko join karein:", reply_markup=keyboard)

async def main():
    await bot.set_webhook(f"{os.getenv('RENDER_EXTERNAL_URL')}/webhook")
    print("Bot started with webhook")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
