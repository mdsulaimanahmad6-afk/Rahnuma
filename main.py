import os
import json
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import Command
from motor.motor_asyncio import AsyncIOMotorClient
from aiohttp import web

# --- Environment Variables ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = "@Rahnuma_e_Deen"
MINI_APP_URL = os.getenv("MINI_APP_URL", "https://rahnuma-rr6r.onrender.com/frontend/index.html")
MONGO_URI = os.getenv("MONGO_URI")

# --- Initialization ---
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# MongoDB Connection
client = AsyncIOMotorClient(MONGO_URI)
db = client['telegram_bot_db']
users_collection = db['verified_users']

@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    
    # 1. Check if User is already verified
    try:
        user_data = await users_collection.find_one({"user_id": user_id})
        if user_data and user_data.get("is_verified"):
            await message.answer("✅ Aap already verified hain! Aap bot use kar sakte hain.")
            return
    except Exception as e:
        print(f"Database error: {e}")

    # 2. Check Channel Membership
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        if member.status in ["member", "administrator", "creator"]:
            await users_collection.update_one(
                {"user_id": user_id},
                {"$set": {"is_verified": True, "name": message.from_user.first_name}},
                upsert=True
            )
            await message.answer("✅ Verification successful! Ab aap bot use kar sakte hain.")
            return
    except Exception as e:
        print(f"Channel check error: {e}")

    # 3. Send Force Join Buttons
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Channel Join Karein", url="https://t.me/Rahnuma_e_Deen")],
        [InlineKeyboardButton(text="🛡️ Verify Now", web_app=WebAppInfo(url=MINI_APP_URL))]
    ])
    await message.answer("⚠️ Verification ke liye pehle in channels ko join karein:", reply_markup=keyboard)


# Mini App se data receive karne ka handler
@dp.message()
async def handle_web_app_data(message: types.Message):
    if message.web_app_data:
        try:
            data = json.loads(message.web_app_data.data)
            user_id = data.get("user_id")
            device_info = data.get("device_info")

            if user_id and device_info:
                # 1. Check karein ki kya is device se koi aur account pehle verify ho chuka hai
                existing_device_user = await users_collection.find_one({
                    "device_info.userAgent": device_info.get("userAgent"),
                    "device_info.screen": device_info.get("screen"),
                    "user_id": {"$ne": user_id} # Doosre ID ka check
                })
                
                if existing_device_user:
                    # Agar device pehle se linked hai, toh Block message bhejein
                    await message.answer("⛔ Blocked: This device is already linked to another user.")
                    return

                # 2. Agar device naya hai, toh save karein aur Success bhejein
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


# --- Web Server & Webhook Setup ---

async def main():
    render_url = os.getenv('RENDER_EXTERNAL_URL')
    
    if render_url:
        await bot.delete_webhook(drop_pending_updates=True)
        webhook_path = f"/webhook/{BOT_TOKEN}"
        await bot.set_webhook(f"{render_url}{webhook_path}")
        print(f"Webhook set to {render_url}{webhook_path}")
        
        app = web.Application()
        
        async def health_check(request):
            return web.Response(text="Bot is alive!")
        app.router.add_get("/", health_check)
        
        async def webhook_handler(request):
            update = types.Update(**(await request.json()))
            await dp.feed_update(bot, update)
            return web.Response(text="OK")
        app.router.add_post(webhook_path, webhook_handler)
        
        # Frontend files serve karein
        app.router.add_static('/frontend', path='frontend', name='frontend')
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", 8080)
        await site.start()
        print("Server started on port 8080.")
        
        await asyncio.Event().wait()
    else:
        print("Running in polling mode (Local)")
        await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
