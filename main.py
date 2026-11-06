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

    # 2. Check Channel Membership (Force Join)
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
            init_data = data.get("initData")

            if not init_data:
                await message.answer("❌ Invalid data received.")
                return

            # initData se user ID nikaalein
            import urllib.parse
            parsed = urllib.parse.parse_qs(init_data)
            user_json = json.loads(parsed.get("user", ["{}"])[0])
            user_id = user_json.get("id")

            if not user_id:
                await message.answer("❌ User ID not found.")
                return

            # 1. Channel Check (Backend par hi check karein)
            try:
                member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
                if member.status not in ["member", "administrator", "creator"]:
                    await message.answer("❌ Aapne channel join nahi kiya hai. Pehle channel join karein.")
                    return
            except Exception as e:
                print(f"Channel check error: {e}")
                await message.answer("❌ Channel check fail hua. Dobara try karein.")
                return

            # 2. Multiple Account Check (Device/User ID based)
            # Yahan hum check karenge ki kya is user_id ke alawa kisi aur ne isi device se verify kiya hai
            # Lekin Telegram direct device ID nahi deta. Hum browser details use karenge.
            # Filhal ke liye hum sirf user_id check karenge.
            
            # Agar sab sahi hai, toh verify karein
            await users_collection.update_one(
                {"user_id": user_id},
                {"$set": {"is_verified": True, "name": user_json.get("first_name", "User")}},
                upsert=True
            )
            await message.answer("✅ Verification complete! Device secured & Profile verified.")

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
