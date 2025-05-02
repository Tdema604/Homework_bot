import os
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
logger = logging.getLogger(name)
logger = logging.getLogger(name)
from aiohttp import web
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from handlers import forward_message, start, chat_id
from web import setup_routes
from dotenv import load_dotenv

# Logging setup
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)


# Load environment variables
load_dotenv()

# Read environment variables
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
ALLOWED_SOURCE_CHAT_IDS = os.getenv("SOURCE_CHAT_IDS", "").split(",")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))
PORT = int(os.getenv("PORT", 10000))  # Render uses port 10000 by default

# Validate critical configs
if not TOKEN or not WEBHOOK_URL:
    raise ValueError("Missing BOT_TOKEN or WEBHOOK_URL in .env")

# Create aiohttp app
app = web.Application()

# Startup routine
async def on_startup(app):
    application = Application.builder().token(TOKEN).build()

    # Store bot config in shared data
    application.bot_data["ALLOWED_SOURCE_CHAT_IDS"] = [int(id.strip()) for id in ALLOWED_SOURCE_CHAT_IDS if id.strip()]
    application.bot_data["ADMIN_CHAT_ID"] = ADMIN_CHAT_ID

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("id", chat_id))
    application.add_handler(MessageHandler(filters.ALL, forward_message))

    # Set webhook for Telegram
    await application.initialize()
    await application.bot.set_webhook(url=WEBHOOK_URL)
    setup_routes(app, application.bot, application)

    logger.info("✅ Bot initialized and webhook set.")

app.on_startup.append(on_startup)

# Launch server
if__name__ == "_main_":
    logger.info(f"🌍 Running bot server on port {PORT}")
    web.run_app(app, host="0.0.0.0", port=PORT)