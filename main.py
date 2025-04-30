import logging
import os
import asyncio
from aiohttp import web
from telegram import Bot
from telegram.ext import Application, MessageHandler, filters  # Ensure these are imported correctly
from handlers import forward_message
from utils import load_env
from web import setup_routes

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

    # Initialize the Application object
    application = Application.builder().token(TOKEN).build()

    # Inject bot data (IDs) for handler access
    application.bot_data["SOURCE_CHAT_ID"] = SOURCE_CHAT_ID
    application.bot_data["TARGET_CHAT_ID"] = TARGET_CHAT_ID
    application.bot_data["ADMIN_CHAT_ID"] = ADMIN_CHAT_ID

    # Add the main message handler to handle all types of messages
    application.add_handler(MessageHandler(filters.ALL, forward_message))

    # Set up webhook + health routes
    app = web.Application()
    setup_routes(app, bot, application)

    # Set webhook
    await bot.set_webhook(url=WEBHOOK_URL)
    logger.info("🚀 Webhook set successfully.")

    # Start aiohttp server
    logger.info("🌐 Serving via aiohttp...")
    web.run_app(app, host="0.0.0.0", port=8080)

if __name__ == '__main__':
    try:
        # Run the async main function using asyncio
        asyncio.run(main())  # Use asyncio.run() to run the main coroutine
    except Exception as e:
        logger.error(f"Startup failed: {e}")
