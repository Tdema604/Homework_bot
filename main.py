import logging
import os
from aiohttp import web
from dotenv import load_dotenv
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram import Update
from handlers import (
    start_handler,
    status_command,
    id_command,
    help_command,
    list_routes_command,
    add_routes_command,
    delete_routes_command,
    list_senders_command,
    clear_senders_command,
    get_weekly_summary_command,
    feedback_command,
    handle_message,
    reload_config,
)
from utils import (
    is_admin,
    is_junk_message,
    get_target_chat_id,
    extract_text_from_image,
    transcribe_audio_with_whisper,
    is_homework_text,
    forward_homework,
    get_weekly_summary,
    clear_homework_log,
    track_sender_activity,
    list_sender_activity,
    clear_sender_data,
    parse_routes_map,
    add_route_to_env,
    delete_route_from_env,
)

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", 8443))

# Safely handle empty ADMIN_CHAT_IDS
admin_chat_ids = os.getenv("ADMIN_CHAT_IDS", "").strip()
if admin_chat_ids:
    ADMIN_CHAT_IDS = list(map(int, admin_chat_ids.split(",")))
else:
    ADMIN_CHAT_IDS = []
    print("⚠️ Warning: ADMIN_CHAT_IDS not found or is empty. Using empty list.")

# ✅ Always print the final loaded value, whether empty or not:
print(f"ADMIN_CHAT_IDS loaded as: {ADMIN_CHAT_IDS}")


# Parse ROUTES_MAP
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
        print("⚠️ Invalid ROUTES_MAP format in .env. Expecting format like '123:456,789:1011'.")

# Logging setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

async def on_startup(app: web.Application):
    logging.info("🚀 Bot started via webhook.")
    for admin_id in ADMIN_CHAT_IDS:
        try:
            await app["bot"].send_message(chat_id=admin_id, text="✅ Bot is now running.")
        except Exception as e:
            logging.error(f"❌ Failed to notify admin {admin_id}: {e}")

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Store shared data
    app.bot_data["ROUTES_MAP"] = ROUTES_MAP
    app.bot_data["ADMIN_CHAT_IDS"] = ADMIN_CHAT_IDS
    app.bot_data["FORWARDED_LOGS"] = []
    app.bot_data["SENDER_ACTIVITY"] = {}

    # Webhook setup
    aio_app = web.Application()
    aio_app["bot"] = app.bot
    aio_app.on_startup.append(on_startup)

    async def handle_telegram_request(request):
        data = await request.json()
        update = Update.de_json(data, app.bot)
        await app.update_queue.put(update)
        return web.Response()

    aio_app.router.add_post("/webhook", handle_telegram_request)

    app.router.add_post(WEBHOOK_PATH, bot.webhook_handler())

    # Admin Command Handlers
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("id", id_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("list_routes", list_routes_command))
    app.add_handler(CommandHandler("add_routes", add_routes_command))
    app.add_handler(CommandHandler("delete_routes", delete_routes_command))
    app.add_handler(CommandHandler("feedback", feedback_command))
    app.add_handler(CommandHandler("reload_config", reload_config, filters=filters.User(ADMIN_CHAT_IDS)))
    app.add_handler(CommandHandler("get_weekly_summary", get_weekly_summary, filters=filters.User(ADMIN_CHAT_IDS)))
    app.add_handler(CommandHandler("clear_homework_log", clear_homework_log, filters=filters.User(ADMIN_CHAT_IDS)))
    app.add_handler(CommandHandler("list_senders", list_senders_command, filters=filters.User(ADMIN_CHAT_IDS)))
    app.add_handler(CommandHandler("clear_sender_data", clear_sender_data, filters=filters.User(ADMIN_CHAT_IDS)))

    # Unified message handler
    app.add_handler(MessageHandler(filters.ALL, handle_message))

    # ✅ Set the webhook
    await app.bot.set_webhook(WEBHOOK_URL)

    # ✅ Run aiohttp webhook server
    runner = web.AppRunner(aio_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    # ✅ Notify admins that bot has started
    for admin_id in ADMIN_CHAT_IDS:
        try:
            await app.bot.send_message(admin_id, "✅ Bot started and webhook is set.")
        except Exception as e:
            print(f"Failed to notify admin: {e}")

    # ✅ Keep the bot alive
    await asyncio.Event().wait()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
