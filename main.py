import logging
import os
from dotenv import load_dotenv
from aiohttp import web
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)

# Load env vars
load_dotenv()

# --- Logging ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Environment setup ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", 8443))
ADMIN_CHAT_IDS = list(map(int, os.getenv("ADMIN_CHAT_IDS", "").split(",")))

# ROUTES_MAP from .env in format "123:456,789:1011"
ROUTES_MAP = {}
for route in os.getenv("ROUTES_MAP", "").split(","):
    try:
        src, dst = map(int, route.strip().split(":"))
        ROUTES_MAP[src] = dst
    except ValueError:
        logger.warning(f"Invalid route format: {route}")

# --- Handlers ---
from handlers import (
    start,
    help_command,
    status,
    get_id,
    handle_message,
    list_senders,
    clear_senders,
    list_routes,
    add_route,
    delete_route,
    weekly_summary,
    clear_homework_log,
    reload_config,
)

# ✅ utils import (lazy-loading + model warmup)
from utils import warmup_transcriber

# --- Init App ---
application = ApplicationBuilder().token(BOT_TOKEN).build()

application.bot_data["ROUTES_MAP"] = ROUTES_MAP
application.bot_data["ADMIN_CHAT_IDS"] = ADMIN_CHAT_IDS
application.bot_data["FORWARDED_LOGS"] = []
application.bot_data["SPAM_SENDERS"] = {}

# --- Webhook Handler ---
async def handle_webhook(request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return web.Response()

# --- Startup Logic ---
async def on_startup(app):
    logger.info("Running startup model checks...")
    await warmup_transcriber()
    logger.info("Startup model checks complete.")
    for admin_id in ADMIN_CHAT_IDS:
        try:
            await application.bot.send_message(
                chat_id=admin_id,
                text="✅ Homework Bot is live and webhook is running!",
            )
        except Exception as e:
            logger.warning(f"Failed to notify admin {admin_id}: {e}")

# --- Register Commands ---
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(CommandHandler("status", status))
application.add_handler(CommandHandler("id", get_id))

application.add_handler(CommandHandler("list_senders", list_senders))
application.add_handler(CommandHandler("clear_senders", clear_senders))
application.add_handler(CommandHandler("list_routes", list_routes))
application.add_handler(CommandHandler("add_route", add_route))
application.add_handler(CommandHandler("delete_route", delete_route))
application.add_handler(CommandHandler("weekly_summary", weekly_summary))
application.add_handler(CommandHandler("clear_homework_log", clear_homework_log))
application.add_handler(CommandHandler("reload_config", reload_config))

application.add_handler(MessageHandler(filters.ALL, handle_message))

# --- Run Webhook ---
app = web.Application()
app.router.add_post("/", handle_webhook)
app.on_startup.append(on_startup)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=PORT)
