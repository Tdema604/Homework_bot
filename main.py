import os
import logging
from aiohttp import web
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler
from telegram.ext import (Application, ApplicationBuilder, CommandHandler, MessageHandler, filters )
from dotenv import load_dotenv 
from handlers import (
    start, chat_ids, status, reload_config, help_command,
    list_routes, add_routes, remove_routes,
    list_senders, clear_senders,forward_message,
    weekly_summary, clear_homework_log
)
from utils import get_routes_map, get_admin_ids
from datetime import datetime
import pytz


# Load environment variables from .env file
load_dotenv()

# Fetching environment variables
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Ensure this is the correct Render URL

if not WEBHOOK_URL or not BOT_TOKEN:
    raise ValueError("Missing required environment variables: WEBHOOK_URL or BOT_TOKEN")

PORT = int(os.getenv("PORT", 10000))  # Default to 10000 if PORT isn't set
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook")
BOT_VERSION = "v1.3.2"

# Create application instance and bot
app = ApplicationBuilder().token(BOT_TOKEN).build()
bot = app.bot  # Access bot object directly

# Initialize bot_data
app.bot_data = {
    "ROUTES_MAP": {},  # Initialize empty dictionary for routes map
    "ALLOWED_SOURCE_CHAT_IDS": [],
    "ADMIN_CHAT_IDS": [],
}

# Fetch and parse ROUTES_MAP from .env
routes_env = os.getenv("ROUTES_MAP", "").strip()
if routes_env:
    try:
        routes_map = {
            str(source): [int(dest) for dest in destinations.split(",")]
            for source, destinations in (item.split(":") for item in routes_env.split(","))
        }
        app.bot_data["ROUTES_MAP"] = routes_map
        logging.info(f"✅ Loaded ROUTES_MAP: {routes_map}")
    except ValueError as e:
        logging.error(f"Error parsing ROUTES_MAP: {e}")
else:
    logging.warning("⚠️ ROUTES_MAP environment variable is missing or empty!")

# Register other bot data as necessary
app.bot_data["ALLOWED_SOURCE_CHAT_IDS"] = [
    int(cid.strip()) for cid in os.getenv("SOURCE_CHAT_IDS", "").split(",") if cid.strip()
]
admin_ids_raw = os.getenv("ADMIN_IDS", "").strip()
if admin_ids_raw:
    app.bot_data["ADMIN_CHAT_IDS"] = {int(x.strip()) for x in admin_ids_raw.split(",") if x.strip()}

# Logging Setup
if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN environment variable is missing!")

app = ApplicationBuilder().token(BOT_TOKEN).build()

WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", 10000))
WEBHOOK_PATH = "/webhook"
BOT_VERSION = "v1.3.2"

# ─── Parse ADMIN_IDS Early ─────────────────────────────────
admin_ids_raw = os.getenv("ADMIN_IDS", "").strip()
if not admin_ids_raw:
    logging.warning("⚠️ ADMIN_IDS environment variable is either missing or empty!")
    ADMIN_IDS = set()
else:
    try:
        ADMIN_IDS = {int(x.strip()) for x in admin_ids_raw.split(",") if x.strip().isdigit()}
        if not ADMIN_IDS:
            raise ValueError("No valid admin IDs found after parsing.")
    except ValueError as e:
        logging.error(f"❌ Error while parsing ADMIN_IDS: {e}")
        ADMIN_IDS = set()
logging.info(f"✅ Loaded ADMIN_IDS: {ADMIN_IDS}")

ALLOWED_SOURCE_CHAT_IDS = [
    int(cid.strip()) for cid in os.getenv("SOURCE_CHAT_IDS", "").split(",") if cid.strip()
]

# ─── Logging Setup ──────────────────────────────────────────
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── Handler Registration ──────────────────────────────────
def setup_bot_handlers(application):
    command_handlers = [
        ("start", start),
        ("id", chat_ids),
        ("status", status),
        ("help", help_command),
        ("reload", reload_config),
        ("listroutes", list_routes),
        ("addroutes", add_routes),
        ("removeroutes", remove_routes),
        ("list_senders", list_senders),
        ("clear_senders", clear_senders),
        ("weekly_summary", weekly_summary),
        ("clear_homework_log", clear_homework_log),
    ]
    for cmd, handler in command_handlers:
        application.add_handler(CommandHandler(cmd, handler))

        app.add_handler(CommandHandler(cmd, handler))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(MessageHandler(filters.ALL, forward_message))

# ─── Webhook Setup ────────────────────────────────────────
async def on_startup(app):
    # Set the webhook URL (updated for new Application structure)
    webhook_url = WEBHOOK_URL + WEBHOOK_PATH
    await bot.set_webhook(url=webhook_url)  # Using bot object here
    logger.info(f"✅ Webhook registered with URL: {webhook_url}")

# aiohttp Webhook Handler
async def webhook(request):
    try:
        json_data = await request.json()
        update = Update.de_json(json_data, bot)  # Using bot object here
        await app.process_update(update)
        return web.Response(status=200)
    except Exception as e:
        logger.error(f"❌ Webhook processing error: {e}")
        return web.Response(status=500)

# ─── Admin Notification ─────────────────────────────────────
async def notify_admin(bot, webhook_url):
    try:
        if not ADMIN_IDS:
            logger.info(f"✅ RUNTIME ROUTES_MAP raw string: {os.getenv('ROUTES_MAP')}")
            return

        routes = telegram_app.bot_data.get("ROUTES_MAP", {})
        route_count = len(routes)
        bt_time = datetime.now(pytz.timezone("Asia/Thimphu"))
        timestamp = bt_time.strftime("%Y-%m-%d %H:%M:%S")

        message = (
            f"🤖 <b>Bot restarted</b> ({BOT_VERSION})\n"
            f"🕒 <b>Time:</b> {timestamp} (BTT)\n"
            f"🗺️ <b>Active Routes:</b> {route_count}\n"
            f"🌐 <b>Webhook URL:</b> {webhook_url}"
        )

        for admin_chat_id in ADMIN_IDS:
            await bot.send_message(admin_chat_id, message, parse_mode="HTML")

        logger.info("✅ Admin(s) notified.")
    except Exception as e:
        logger.error(f"❌ Failed to notify admin(s): {e}")

# ─── aiohttp Startup Hook ───────────────────────────────────
async def on_startup(app: web.Application):
    logger.info(f"✅ RUNTIME ROUTES_MAP raw string: {os.getenv('ROUTES_MAP')}")
    telegram_app.bot_data["ROUTES_MAP"] = get_routes_map()
    telegram_app.bot_data["ALLOWED_SOURCE_CHAT_IDS"] = ALLOWED_SOURCE_CHAT_IDS
    telegram_app.bot_data["ADMIN_CHAT_IDS"] = ADMIN_IDS

    setup_bot_handlers(telegram_app)
    await telegram_app.initialize()
    await telegram_app.start()

    full_webhook_url = f"{WEBHOOK_URL}{WEBHOOK_PATH}"
    await telegram_app.bot.set_webhook(url=full_webhook_url)
    logger.info(f"✅ Webhook registered with URL: {full_webhook_url}")

    await notify_admin(telegram_app.bot, full_webhook_url)

# ─── Run aiohttp App ────────────────────────────────────────
web_app = web.Application()
web_app.on_startup.append(on_startup)
web_app.router.add_post(WEBHOOK_PATH, webhook)

if __name__ == "__main__":
    logger.info(f"🚀 Launching bot server on port {PORT}")
    # Start the aiohttp server
    web.run_app(web_app, host="0.0.0.0", port=PORT)
    web.run_app(web_app, host="0.0.0.0", port=PORT)

