import logging
import os
import asyncio
from aiohttp import web
from telegram import Bot
from telegram.ext import Application, MessageHandler, filters
from handlers import forward_message, start  # Import handlers for /start and message forwarding
from utils import load_env
from web import setup_routes  # Assuming setup_routes is in web.py

# Set up logging
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Load .env variables
load_env()

# Bot token from .env
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN is missing in the environment variables!")

# Group/Admin chat IDs from .env
SOURCE_CHAT_ID = int(os.getenv("SOURCE_CHAT_ID"))
TARGET_CHAT_ID = int(os.getenv("TARGET_CHAT_ID"))
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))

# Webhook URL from .env
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
if not WEBHOOK_URL:
    raise ValueError("WEBHOOK_URL is missing in the environment variables!")

# Start bot app
async def main():
    bot = Bot(token=TOKEN)

    application = Application.builder().token(TOKEN).build()

    # Inject bot data (IDs) for handler access
    application.bot_data["SOURCE_CHAT_ID"] = SOURCE_CHAT_ID
    application.bot_data["TARGET_CHAT_ID"] = TARGET_CHAT_ID
    application.bot_data["ADMIN_CHAT_ID"] = ADMIN_CHAT_ID

    # Add main message handler and start command handler
    application.add_handler(MessageHandler(filters.ALL, forward_message))
    application.add_handler(MessageHandler(filters.COMMAND, start))

    # Set up the aiohttp app and routes
    app = web.Application()
    setup_routes(app, bot, application)

    # Set webhook
    await bot.set_webhook(url=WEBHOOK_URL)
    logger.info("🚀 Webhook set successfully.")

    # Start aiohttp server with AppRunner
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    logger.info("🌐 Serving via aiohttp...")

if __name__ == '__main__':
    try:
        # Start the event loop
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Startup failed: {e}")
