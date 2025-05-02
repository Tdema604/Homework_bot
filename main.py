import os
import logging
from dotenv import load_dotenv  # ✅ new

from aiohttp import web
from telegram.ext import Application, MessageHandler, filters
from handlers import forward_message, start
from web import setup_routes

# Logging
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ✅ Load env
load_dotenv()


# ENV vars
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
SOURCE_CHAT_ID = int(os.getenv("SOURCE_CHAT_ID"))
TARGET_CHAT_ID = int(os.getenv("TARGET_CHAT_ID"))
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))
PORT = int(os.getenv("PORT", 10000))  # Render default

if not TOKEN or not WEBHOOK_URL:
    raise ValueError("Missing BOT_TOKEN or WEBHOOK_URL in .env")

# Create aiohttp app
app = web.Application()

# 🔁 Telegram init on app startup
async def on_startup(app):
    application = Application.builder().token(TOKEN).build()

    # Store config
    application.bot_data["SOURCE_CHAT_ID"] = SOURCE_CHAT_ID
    application.bot_data["TARGET_CHAT_ID"] = TARGET_CHAT_ID
    application.bot_data["ADMIN_CHAT_ID"] = ADMIN_CHAT_ID

    # Handlers
    application.add_handler(MessageHandler(filters.COMMAND, start))
    application.add_handler(MessageHandler(filters.ALL, forward_message))

    await application.initialize()
    await application.bot.set_webhook(url=WEBHOOK_URL)
    logger.info("🚀 Webhook set successfully.")

    setup_routes(app, application.bot, application)
    logger.info("✅ Routes registered.")

app.on_startup.append(on_startup)

# 🔥 Bind port directly (important for Render)
if __name__ == "__main__":
    logger.info(f"🌍 Starting app on port {PORT}")
    web.run_app(app, host="0.0.0.0", port=PORT)
