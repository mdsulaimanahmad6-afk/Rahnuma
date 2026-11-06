import os
import json
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import Command
from motor.motor_asyncio import AsyncIOMotorClient
from aiohttp import web

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = "@Rahnuma_e_Deen"
MINI_APP_URL = os.getenv("MINI_APP_URL", "https://your-app.onrender.com")
MONGO_URI = os.getenv("MONGO_URI")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = AsyncIOMotorClient(MONGO_URI)
db = client['telegram_bot_db']
users_collection = db['verified_users']

# ... (aapke start aur handle_web_app_data handlers yahan rahenge, unhe waise hi rehne dein) ...

async def main():
    # Sabse pehle purana webhook delete karein
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Render ka URL lein
    render_url = os.getenv('RENDER_EXTERNAL_URL')
    
    if render_url:
        # Webhook set karein
        webhook_path = f"/webhook/{BOT_TOKEN}"
        await bot.set_webhook(f"{render_url}{webhook_path}")
        print(f"Webhook set to {render_url}{webhook_path}")
        
        # aiohttp server banayein jo Render ke health check ko respond kare
        app = web.Application()
        
        # Health check route (taaki Render ko port mile)
        async def health_check(request):
            return web.Response(text="OK")
        app.router.add_get("/", health_check)
        
        # Webhook route
        async def webhook_handler(request):
            update = types.Update(**(await request.json()))
            await dp.feed_update(bot, update)
            return web.Response(text="OK")
        app.router.add_post(webhook_path, webhook_handler)
        
        # Server start karein (Render port 8080 expect karta hai)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", 8080)
        await site.start()
        print("Server started on port 8080")
        
        # Server ko chalta rakhein
        await asyncio.Event().wait()
    else:
        # Local testing ke liye polling
        print("Running in polling mode")
        await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
