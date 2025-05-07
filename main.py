import os
import logging
from aiohttp import web
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, filters
)
from dotenv import load_dotenv
from handlers import (
    start, chat_id, status, reload_config, help_command,
    list_routes, add_routes, remove_routes,
    list_senders, clear_senders,
    weekly_homework, clear_homework_log,
    forward_message
)
from utils import get_routes_map, get_admin_ids
from datetime import datetime
import pytz

# ─── Load Environment Variables ─────────────────────────────
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", 10000))
WEBHOOK_PATH = "/webhook"
ADMIN_CHAT_IDS = int(os.getenv("ADMIN_CHAT_ID", "0"))
ALLOWED_SOURCE_CHAT_IDS = [
    int(cid.strip()) for cid in os.getenv("SOURCE_CHAT_IDS", "").split(",") if cid.strip()
]

BOT_VERSION = "v1.3.2"

# ─── Logging Setup ──────────────────────────────────────────
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── Build Telegram Application ─────────────────────────────
telegram_app = Application.builder().token(BOT_TOKEN).build()

# ─── Handler Registration ──────────────────────────────────
def setup_bot_handlers(app: Application):
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
        ("weekly_homework", weekly_homework),
        ("clear_homework_log", clear_homework_log),
    ]
    for cmd, handler in command_handlers:
        app.add_handler(CommandHandler(cmd, handler))
    app.add_handler(MessageHandler(filters.ALL, forward_message))

# ─── aiohttp Webhook Handler ────────────────────────────────
async def webhook(request):
    try:
        json_data = await request.json()
        update = Update.de_json(json_data, telegram_app.bot)
        await telegram_app.process_update(update)
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
    logger.warning(f"✅ RUNTIME ROUTES_MAP raw string: {os.getenv('ROUTES_MAP')}")
    telegram_app.bot_data["ROUTES_MAP"] = get_routes_map()
    telegram_app.bot_data["ALLOWED_SOURCE_CHAT_IDS"] = ALLOWED_SOURCE_CHAT_IDS
    telegram_app.bot_data["ADMIN_CHAT_IDS"] = ADMIN_IDS

    setup_bot_handlers(telegram_app)
    await telegram_app.initialize()
    await telegram_app.start()

    full_webhook_url = f"{WEBHOOK_URL}{WEBHOOK_PATH}"
    await telegram_app.bot.set_webhook(url=full_webhook_url)
    logger.info(f"✅ Webhook registered with URL: {full_webhook_url}")

    for admin_id in ADMIN_IDS:
        await notify_admin(telegram_app.bot, full_webhook_url)

# ─── Load ADMIN_IDS Safely ──────────────────────────────────
admin_ids_raw = os.getenv("ADMIN_IDS", "").strip()

if not admin_ids_raw:
    logger.warning("⚠️ ADMIN_IDS environment variable is either missing or empty!")
    ADMIN_IDS = set()
else:
    try:
        ADMIN_IDS = {int(x.strip()) for x in admin_ids_raw.split(",") if x.strip().isdigit()}
        if not ADMIN_IDS:
            raise ValueError("No valid admin IDs found after parsing.")
    except ValueError as e:
        logger.error(f"❌ Error while parsing ADMIN_IDS: {e}")
        ADMIN_IDS = set()

logger.warning(f"✅ Loaded ADMIN_IDS: {ADMIN_IDS}")

# ─── Run aiohttp App ────────────────────────────────────────
web_app = web.Application()
web_app.on_startup.append(on_startup)
web_app.router.add_post(WEBHOOK_PATH, webhook)

if __name__ == "__main__":
    logger.info(f"🚀 Launching bot server on port {PORT}")
    web.run_app(web_app, host="0.0.0.0", port=PORT)