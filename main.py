import os
import logging
from aiohttp import web
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from dotenv import load_dotenv
from handlers import forward_message, start, chat_id, status, reload_config, list_routes, add_routes, remove_routes
from web import setup_routes
from utils import get_route_map

# Logging setup
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Required .env vars
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
ALLOWED_SOURCE_CHAT_IDS = os.getenv("SOURCE_CHAT_IDS", "").split(",")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0") or "0")
PORT = int(os.getenv("PORT", 10000))  # Render default

if not TOKEN or not WEBHOOK_URL:
    raise ValueError("❌ Missing BOT_TOKEN or WEBHOOK_URL in .env")

# aiohttp app instance
app = web.Application()

# aiohttp startup hook
async def on_startup(app):
    application = Application.builder().token(TOKEN).build()

    # Inject runtime bot data
    application.bot_data["ALLOWED_SOURCE_CHAT_IDS"] = [int(id.strip()) for id in ALLOWED_SOURCE_CHAT_IDS if id.strip()]
    application.bot_data["ADMIN_CHAT_ID"] = ADMIN_CHAT_ID
    application.bot_data["ROUTE_MAP"] = get_route_map()

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("id", chat_id))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("reload", reload_config))
    application.add_handler(CommandHandler("listroutes", list_routes))
    application.add_handler(CommandHandler("addroutes", add_routes))
    application.add_handler(CommandHandler("removeroutes", remove_routes))

    # Message handler
    application.add_handler(MessageHandler(filters.ALL, forward_message))

    # Bot initialization
    await application.initialize()
    await application.bot.set_webhook(url=WEBHOOK_URL)

    # Setup webhook routes
    setup_routes(app, application.bot, application)

    logger.info("✅ Bot initialized and webhook set successfully.")

    # Notify admin on startup
    try:
        route_map = application.bot_data["ROUTE_MAP"]
        await application.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"🤖 Bot restarted.\n🗺️ Routes loaded: {len(route_map)}\n🌐 Webhook URL: `{WEBHOOK_URL}`",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.warning(f"⚠️ Failed to notify admin: {e}")

# Register startup event
app.on_startup.append(on_startup)

# Run aiohttp app
if __name__ == "__main__":
    logger.info(f"🚀 Starting bot server on port {PORT} ...")
    web.run_app(app, host="0.0.0.0", port=PORT)
