import os
import logging
from aiohttp import web
from telegram import Update
from telegram.ext import ApplicationBuilder
from dotenv import load_dotenv
from handlers import setup_bot_handlers
from utils import get_routes_map
from datetime import datetime
import pytz

# Load environment variables
load_dotenv()

# ─── Config & Logging ───────────────────────────────────────
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", 10000))
WEBHOOK_PATH = "/webhook"
BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_VERSION = "v1.3.2"

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── Telegram Application ───────────────────────────────────
telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()
bot = telegram_app.bot

# Initialize bot_data
bot_data = telegram_app.bot_data
bot_data["ROUTES_MAP"] = get_routes_map()
bot_data["ALLOWED_SOURCE_CHAT_IDS"] = [
    int(cid.strip()) for cid in os.getenv("SOURCE_CHAT_IDS", "").split(",") if cid.strip()
]
admin_ids_raw = os.getenv("ADMIN_IDS", "").strip()
bot_data["ADMIN_CHAT_IDS"] = {int(x.strip()) for x in admin_ids_raw.split(",") if x.strip()} if admin_ids_raw else set()

# Register all handlers
setup_bot_handlers(telegram_app)

# ─── Webhook Handler ────────────────────────────────────────
async def webhook(request):
    try:
        data = await request.json()
        update = Update.de_json(data, bot)
        await telegram_app.process_update(update)
        return web.Response(status=200)
    except Exception as e:
        logger.error(f"❌ Webhook processing error: {e}")
        return web.Response(status=500)

# ─── Admin Notification ─────────────────────────────────────
async def notify_admins():
    if not bot_data["ADMIN_CHAT_IDS"]:
        logger.warning("No admin IDs to notify.")
        return

    bt_time = datetime.now(pytz.timezone("Asia/Thimphu"))
    formatted_time = bt_time.strftime("%I:%M %p")  # Format as 12-hour time with AM/PM
    route_count = len(bot_data["ROUTES_MAP"])
    webhook_url = "https://homework-bot-wxi3.onrender.com/webhook"  # You should have the webhook URL stored or calculated earlier in your code

    message = (
        f"🤖 <b>Bot restarted</b> ({BOT_VERSION})\n"
        f"🕒 <b>Time:</b> {formatted_time} (BTT)\n"
        f"🗺️ <b>Active Routes:</b> {route_count}\n"
        f"🌐 <b>Webhook URL:</b> {webhook_url}"
    )

    # Send the message to all admin chat IDs
    for admin_id in bot_data["ADMIN_CHAT_IDS"]:
        try:
            await bot.send_message(chat_id=admin_id, text=message, parse_mode="HTML")
        except Exception as e:
            logger.error(f"❌ Failed to notify admin {admin_id}: {e}")


# ─── aiohttp Lifecycle Hooks ────────────────────────────────
async def on_startup(_):
    await telegram_app.initialize()
    await telegram_app.start()
    await bot.set_webhook(WEBHOOK_URL + WEBHOOK_PATH)
    logger.info("✅ Bot initialized and webhook set.")
    await notify_admins()

async def on_cleanup(_):
    await telegram_app.stop()
    logger.info("🛑 Bot stopped.")

# ─── aiohttp Web App ────────────────────────────────────────
web_app = web.Application()
web_app.add_routes([web.post(WEBHOOK_PATH, webhook)])
web_app.on_startup.append(on_startup)
web_app.on_cleanup.append(on_cleanup)

# ─── Run Server ─────────────────────────────────────────────
if __name__ == "__main__":
    logger.info(f"🚀 Launching bot server on port {PORT}")
    web.run_app(web_app, host="0.0.0.0", port=PORT)
