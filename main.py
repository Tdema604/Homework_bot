import os
import logging
from aiohttp import web
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler
from dotenv import load_dotenv
from handlers import setup_bot_handlers  # Ensure this is properly imported

# Load environment variables from .env file
load_dotenv()

# Fetching environment variables
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Ensure this is the correct Render URL
BOT_TOKEN = os.getenv("BOT_TOKEN")
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
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── Handler Registration ──────────────────────────────────
def setup_bot_handlers(application):
    command_handlers = [
        ("start", start),
        ("id", chat_id),
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

# aiohttp web application setup
web_app = web.Application()
web_app.on_startup.append(on_startup)
web_app.router.add_post(WEBHOOK_PATH, webhook)

if __name__ == "__main__":
    logger.info(f"🚀 Launching bot server on port {PORT}")
    # Start the aiohttp server
    web.run_app(web_app, host="0.0.0.0", port=PORT)
