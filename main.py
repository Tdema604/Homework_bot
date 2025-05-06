import os
import logging
from aiohttp import web
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ApplicationBuilder, PicklePersistence
)
from dotenv import load_dotenv
from handlers import (
    start, chat_id, status, reload_config,
    list_routes, add_routes, remove_routes,
    list_senders, clear_senders,
    weekly_homework, clear_homework_log,
    forward_message, notify_admin
)
from web import setup_routes
from utils import get_route_map

# ─── Logging Setup ──────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ─── Load Environment Variables ─────────────────────────────────────────────────
load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))
ALLOWED_SOURCE_CHAT_IDS = [
    int(cid.strip()) for cid in os.getenv("SOURCE_CHAT_IDS", "").split(",") if cid.strip()
]
PORT = int(os.getenv("PORT", 10000))  # Default for Render or local

if not TOKEN or not WEBHOOK_URL:
    raise ValueError("❌ BOT_TOKEN or WEBHOOK_URL not found in .env")

# ─── aiohttp App Instance ───────────────────────────────────────────────────────
app = web.Application()

# ─── Register Bot Command Handlers ──────────────────────────────────────────────
def setup_bot_handlers(application: Application):
    command_handlers = [
        ("start", start),
        ("id", chat_id),
        ("status", status),
        ("reload", reload_config),
        ("listroutes", list_routes),
        ("addroutes", add_routes),
        ("removeroutes", remove_routes),
        ("list_senders", list_senders),
        ("clear_senders", clear_senders),
        ("weekly_homework", weekly_homework),
        ("clear_homework_log", clear_homework_log),
    ]

    for cmd, handler in command_handlers:
        application.add_handler(CommandHandler(cmd, handler))

    # Catch-all message forwarder
    application.add_handler(MessageHandler(filters.ALL, forward_message))


# ─── Bot Startup Routine ────────────────────────────────────────────────────────
async def on_startup(app: web.Application):
    # Persistent storage
    persistence = PicklePersistence(filepath="bot_data.pkl")
    application = Application.builder().token(TOKEN).persistence(persistence).build()

    # Always reload ROUTE_MAP from JSON file (avoid relying on persistence)
    logger.info("🔄 Forcing fresh ROUTE_MAP load from routes.json...")
    application.bot_data["ROUTE_MAP"] = get_route_map()

    application.bot_data["ALLOWED_SOURCE_CHAT_IDS"] = ALLOWED_SOURCE_CHAT_IDS
    application.bot_data["ADMIN_CHAT_ID"] = ADMIN_CHAT_ID

    logger.info(f"📦 ROUTE_MAP: {application.bot_data['ROUTE_MAP']}")

    # Setup handlers
    setup_bot_handlers(application)

    # Webhook Setup
    await application.initialize()
    await application.bot.set_webhook(url=WEBHOOK_URL)

    # Setup aiohttp → Telegram bridge
    setup_routes(app, application.bot, application)

    logger.info("✅ Bot initialized and webhook registered")

    # Notify admin
    await notify_admin(application, ADMIN_CHAT_ID, WEBHOOK_URL)


# ─── aiohttp Lifecycle Hook ─────────────────────────────────────────────────────
app.on_startup.append(on_startup)

# ─── Run Server ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logger.info(f"🚀 Launching bot server on port {PORT}")
    web.run_app(app, host="0.0.0.0", port=PORT)
