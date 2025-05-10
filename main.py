import logging
import os
import asyncio
from aiohttp import web
from dotenv import load_dotenv
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters
)
from handlers import (
    start_handler, status_command, id_command, help_command,
    list_routes_command, add_routes_command, delete_routes_command,
    list_senders_command, clear_senders_command,
    get_weekly_summary_command, feedback_command,
    handle_message, reload_config
)
from utils import (
    get_weekly_summary, clear_homework_log
)

# Load environment
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook")
PORT = int(os.getenv("PORT", 8443))

# Admin chat IDs
admin_chat_ids = os.getenv("ADMIN_CHAT_IDS", "").strip()
ADMIN_CHAT_IDS = list(map(int, admin_chat_ids.split(","))) if admin_chat_ids else []
print(f"ADMIN_CHAT_IDS loaded as: {ADMIN_CHAT_IDS}")

# Routes map
ROUTES_MAP = {}
raw_routes = os.getenv("ROUTES_MAP", "").strip()
if raw_routes:
    try:
        ROUTES_MAP = {
            int(k): int(v)
            for route in raw_routes.split(",")
            for k, v in [route.split(":")]
        }
    except ValueError:
        print("⚠️ Invalid ROUTES_MAP format in .env.")

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Inject shared data
    app.bot_data["ROUTES_MAP"] = ROUTES_MAP
    app.bot_data["ADMIN_CHAT_IDS"] = ADMIN_CHAT_IDS
    app.bot_data["FORWARDED_LOGS"] = []
    app.bot_data["SENDER_ACTIVITY"] = {}

    # Register command handlers
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("id", id_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("list_routes", list_routes_command))
    app.add_handler(CommandHandler("add_routes", add_routes_command))
    app.add_handler(CommandHandler("delete_routes", delete_routes_command))
    app.add_handler(CommandHandler("feedback", feedback_command))
    app.add_handler(CommandHandler("reload_config", reload_config, filters=filters.User(ADMIN_CHAT_IDS)))
    app.add_handler(CommandHandler("get_weekly_summary", get_weekly_summary_command, filters=filters.User(ADMIN_CHAT_IDS)))
    app.add_handler(CommandHandler("clear_homework_log", clear_homework_log, filters=filters.User(ADMIN_CHAT_IDS)))
    app.add_handler(CommandHandler("list_senders", list_senders_command, filters=filters.User(ADMIN_CHAT_IDS)))
    app.add_handler(CommandHandler("clear_sender_data", clear_senders_command, filters=filters.User(ADMIN_CHAT_IDS)))

    # Unified message handler
    app.add_handler(MessageHandler(filters.ALL, handle_message))

    # Set webhook
    await app.bot.set_webhook(f"{WEBHOOK_URL}{WEBHOOK_PATH}")
    logging.info(f"✅ Webhook set to {WEBHOOK_URL}{WEBHOOK_PATH}")

    # Notify admins
    for admin_id in ADMIN_CHAT_IDS:
        try:
            await app.bot.send_message(admin_id, "✅ Bot is up and webhook is set.")
        except Exception as e:
            logging.warning(f"Failed to notify admin {admin_id}: {e}")

    # Setup aiohttp webhook server
    aio_app = web.Application()
    aio_app.router.add_post(WEBHOOK_PATH, app.webhook_handler())

    runner = web.AppRunner(aio_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logging.info(f"🚀 Bot is running on port {PORT} via aiohttp")

    # Keep alive
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
