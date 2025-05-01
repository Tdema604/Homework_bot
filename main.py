import os
import logging
import asyncio
from aiohttp import web
from telegram.ext import Application, MessageHandler, filters
from handlers import forward_message, start
from utils import load_env
from web import setup_routes

# Set up logging
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_env()

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
SOURCE_CHAT_ID = int(os.getenv("SOURCE_CHAT_ID"))
TARGET_CHAT_ID = int(os.getenv("TARGET_CHAT_ID"))
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))
PORT = int(os.getenv("PORT", 8080))  # Default 8080; Render overrides

if not TOKEN or not WEBHOOK_URL:
    raise ValueError("BOT_TOKEN or WEBHOOK_URL is missing in .env")

# 🌐 Global aiohttp app for gunicorn to detect
app = web.Application()

async def init_bot():
    # Initialize Telegram app
    application = Application.builder().token(TOKEN).build()

    # Store config in bot_data
    application.bot_data["SOURCE_CHAT_ID"] = SOURCE_CHAT_ID
    application.bot_data["TARGET_CHAT_ID"] = TARGET_CHAT_ID
    application.bot_data["ADMIN_CHAT_ID"] = ADMIN_CHAT_ID

    # Register bot handlers
    application.add_handler(MessageHandler(filters.COMMAND, start))
    application.add_handler(MessageHandler(filters.ALL, forward_message))

    # Init bot and set webhook
    await application.initialize()
    await application.bot.set_webhook(url=WEBHOOK_URL)
    logger.info("🚀 Webhook set successfully.")

    # Add Telegram webhook and health check routes
    setup_routes(app, application.bot, application)
    logger.info("✅ Routes registered.")

    # Start aiohttp site
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=PORT)
    await site.start()
    logger.info(f"🌍 Bot live and serving on port {PORT}.")

# Run bot on startup
asyncio.get_event_loop().create_task(init_bot())
