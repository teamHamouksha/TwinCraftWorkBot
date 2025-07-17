import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_webhook
from aiohttp import web

from config import BOT_TOKEN, ADMIN_ID, DB_NAME
from handlers import router
from database import Database

# إعدادات الـ Webhook (إذا كنت ستنشر على Render.com)
WEB_SERVER_HOST = "0.0.0.0"
WEB_SERVER_PORT = int(os.getenv("PORT", 8000)) # المنفذ الذي يستخدمه Render.com
WEBHOOK_PATH = "/webhook"
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "YOUR_WEBHOOK_SECRET_HERE") # استخدم متغير بيئة لـ Webhook Secret
BASE_WEBHOOK_URL = os.getenv("BASE_WEBHOOK_URL", "YOUR_RENDER_APP_URL_HERE") # رابط الـ Webhook العام لبوتك على Render.com

# إعداد التسجيل (Logging)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def main():
    # تهيئة البوت والديسباتشر
    bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.MARKDOWN) # تم تغيير ParseMode إلى Markdown لدعم التنسيق
    dp = Dispatcher()

    # تسجيل الراوتر
    dp.include_router(router)

    # تهيئة قاعدة البيانات
    db = Database(DB_NAME)

    # إعداد الـ webhook إذا تم توفير BASE_WEBHOOK_URL
    if BASE_WEBHOOK_URL and BASE_WEBHOOK_URL != "YOUR_RENDER_APP_URL_HERE":
        logging.info("Setting up webhook...")
        app = web.Application()
        webhook_requests_handler = SimpleRequestHandler(
            dispatcher=dp,
            bot=bot,
            secret_token=WEBHOOK_SECRET,
        )
        webhook_requests_handler.register(app, WEBHOOK_PATH)
        setup_webhook(app, WEBHOOK_PATH)

        # Set webhook URL for the bot
        await bot.set_webhook(
            url=f"{BASE_WEBHOOK_URL}{WEBHOOK_PATH}",
            secret_token=WEBHOOK_SECRET,
            drop_pending_updates=True # إسقاط التحديثات المعلقة عند تعيين الويب هوك
        )

        logging.info(f"Webhook set to: {BASE_WEBHOOK_URL}{WEBHOOK_PATH}")
        print(f"✅ البوت يعمل في وضع الويب هوك على المنفذ {WEB_SERVER_PORT}...")
        web.run_app(app, host=WEB_SERVER_HOST, port=WEB_SERVER_PORT)
    else:
        # تشغيل البوت في وضع الاستطلاع (polling) للتطوير المحلي
        logging.info("Starting bot in polling mode...")
        print("✅ البوت يعمل في وضع الاستطلاع... انتظر استقبال الأوامر")
        await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
