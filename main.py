import os
import logging
from aiohttp import web
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from handlers import forward_message, start, chat_id  # make sure chat_id is defined
from web import setup_routes
from dotenv import load_dotenv

# Logging setup
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Load .env variables
load_dotenv()

# Environment variables
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
ALLOWED_SOURCE_CHAT_IDS = os.getenv("SOURCE_CHAT_IDS", "").split(",")
TARGET_CHAT_ID = int(os.getenv("TARGET_CHAT_ID"))
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))
PORT = int(os.getenv("PORT", 10000))

# Validation
if not TOKEN or not WEBHOOK_URL:
    raise ValueError("Missing BOT_TOKEN or WEBHOOK_URL in .env")

# Create aiohttp app
app = web.Application()

# Start Telegram app
async def on_startup(app):
    application = Application.builder().token(TOKEN).build()

    # Store shared data
    application.bot_data["ALLOWED_SOURCE_CHAT_IDS"] = [int(id.strip()) for id in ALLOWED_SOURCE_CHAT_IDS if id.strip()]
    application.bot_data["TARGET_CHAT_ID"] = TARGET_CHAT_ID
    application.bot_data["ADMIN_CHAT_ID"] = ADMIN_CHAT_ID

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("id", chat_id))
    application.add_handler(MessageHandler(filters.ALL, forward_message))

    await application.initialize()
    await application.bot.set_webhook(url=WEBHOOK_URL)
    setup_routes(app, application.bot, application)

    logger.info("✅ Bot initialized and webhook set.")

app.on_startup.append(on_startup)

if __name__ == "__main__":
    logger.info(f"🌍 Running bot server on port {PORT}")
    web.run_app(app, host="0.0.0.0", port=PORT)
