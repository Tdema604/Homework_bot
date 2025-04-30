import logging
import os
from aiohttp import web
from telegram import Bot
from telegram.ext import Application, MessageHandler, filters
from handlers import forward_message
from utils import load_env
from web import setup_routes  # Assuming you have a setup_routes function in web.py

# Set up logging
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)
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
    # Create bot instance before setting up routes
    bot = Bot(token=TOKEN)

    application = Application.builder().token(TOKEN).build()

    # Inject bot data (IDs) for handler access
    application.bot_data["SOURCE_CHAT_ID"] = SOURCE_CHAT_ID
    application.bot_data["TARGET_CHAT_ID"] = TARGET_CHAT_ID
    application.bot_data["ADMIN_CHAT_ID"] = ADMIN_CHAT_ID

    # Add main message handler
    application.add_handler(MessageHandler(filters.ALL, forward_message))

    # Add webhook + health routes
    app = web.Application()
    setup_routes(app, bot, application)

    # Set webhook
    await bot.set_webhook(url=WEBHOOK_URL)
    logger.info("🚀 Webhook set successfully.")

    # Run the app directly without asyncio.run()
    logger.info("🌐 Serving via aiohttp...")
    port = int(os.getenv("PORT", 8080))  # Default to 8080 if PORT is not set
    await web.run_app(app, host="0.0.0.0", port=port)

if __name__ == '__main__':
    try:
        # Use asyncio.run() to run the main async function correctly
        import asyncio
        asyncio.run(main())  # Use asyncio.run() to run the main coroutine
    except Exception as e:
        logger.error(f"Startup failed: {e}")
