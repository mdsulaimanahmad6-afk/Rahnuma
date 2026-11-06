import os
import json
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import Command
from motor.motor_asyncio import AsyncIOMotorClient # MongoDB library

# Environment Variables (Render par set hongi)
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = "@Rahnuma_e_Deen"
MINI_APP_URL = os.getenv("MINI_APP_URL", "https://your-app.onrender.com")
MONGO_URI = os.getenv("MONGO_URI") # MongoDB Connection String

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# MongoDB Connection Setup
client = AsyncIOMotorClient(MONGO_URI)
db = client['telegram_bot_db'] # Database ka naam
users_collection = db['verified_users'] # Collection (Table) ka naam

@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    
    # 1. Check karein ki user pehle se Database mein verified hai ya nahi
    user_data = await users_collection.find_one({"user_id": user_id})
    if user_data and user_data.get("is_verified"):
        await message.answer("✅ Aap already verified hain! Aap bot use kar sakte hain.")
        return

    # 2. Agar database mein nahi hai, toh channel check karein
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        if member.status in ["member", "administrator", "creator"]:
            # Channel join kar liya hai, toh database mein save karein
            await users_collection.update_one(
                {"user_id": user_id},
                {"$set": {"is_verified": True, "name": message.from_user.first_name}},
                upsert=True
            )
            await message.answer("✅ Verification successful! Ab aap bot use kar sakte hain.")
            return
    except Exception as e:
        print(f"Error checking member: {e}")

    # 3. Agar join nahi kiya, toh Force Join + Mini App button bhejein
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Channel Join Karein", url="https://t.me/Rahnuma_e_Deen")],
        [InlineKeyboardButton(text="🛡️ Verify Now", web_app=WebAppInfo(url=MINI_APP_URL))]
    ])
    await message.answer("⚠️ Verification ke liye pehle in channels ko join karein:", reply_markup=keyboard)


# Mini App (HTML) se data receive karne ka handler
@dp.message()
async def handle_web_app_data(message: types.Message):
    # Jab Mini App se data aayega
    if message.web_app_data:
        try:
            # JSON data ko parse karein
            data = json.loads(message.web_app_data.data)
            user_id = data.get("user_id")
            device_info = data.get("device_info")

            if user_id:
                # Database mein device info save/update karein
                await users_collection.update_one(
                    {"user_id": user_id},
                    {"$set": {"is_verified": True, "device_info": device_info}},
                    upsert=True
                )
                await message.answer("✅ Verification complete! Device secured & Profile verified.")
            else:
                await message.answer("❌ Invalid data received.")
                
        except Exception as e:
            print(f"Error processing web app data: {e}")
            await message.answer("❌ Kuch error aaya. Dobara try karein.")


async def main():
    # Render ke liye Webhook setup
    render_url = os.getenv('RENDER_EXTERNAL_URL')
    if render_url:
        await bot.set_webhook(f"{render_url}/webhook")
        print(f"Webhook set to {render_url}/webhook")
    
    print("Bot started with webhook and MongoDB")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
