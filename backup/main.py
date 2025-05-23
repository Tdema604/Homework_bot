import os
import logging
from aiohttp import web
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from dotenv import load_dotenv
from handlers import forward_message, start, chat_id, status, reload_config
from web import setup_routes
from utils import get_route_map

# Logging setup
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)  # Fixed

# Load environment variables
load_dotenv()

# Required .env vars
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
ALLOWED_SOURCE_CHAT_IDS = os.getenv("SOURCE_CHAT_IDS", "").split(",")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0") or "0")
PORT = int(os.getenv("PORT", 10000))  # Default port for Render

if not TOKEN or not WEBHOOK_URL:
    raise ValueError("Missing BOT_TOKEN or WEBHOOK_URL in .env")

# Create aiohttp web server
app = web.Application()

# On startup
async def on_startup(app):
    application = Application.builder().token(TOKEN).build()

    # Shared bot data
    application.bot_data["ALLOWED_SOURCE_CHAT_IDS"] = [int(id.strip()) for id in ALLOWED_SOURCE_CHAT_IDS if id.strip()]
    application.bot_data["ADMIN_CHAT_ID"] = ADMIN_CHAT_ID
    application.bot_data["ROUTE_MAP"] = get_route_map()  # Fix added here

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("id", chat_id))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("reload", reload_config))
    application.add_handler(MessageHandler(filters.ALL, forward_message))

    # Init bot and webhook
    await application.initialize()
    await application.bot.set_webhook(url=WEBHOOK_URL)
    setup_routes(app, application.bot, application)

    logger.info("Bot initialized and webhook set.")

    try:
        route_map = application.bot_data["ROUTE_MAP"]
        await application.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"Bot restarted.\nRoutes: {len(route_map)} mapped.\nListening via webhook.",
        )
    except Exception as e:
        logger.warning(f"Failed to send startup message to admin: {e}")

# Register startup
app.on_startup.append(on_startup)

# Run bot server
if __name__ == "__main__":
    logger.info(f"Running bot server on port {PORT}")
    web.run_app(app, host="0.0.0.0", port=PORT)