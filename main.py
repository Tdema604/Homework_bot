import logging
import os
import asyncio
from aiohttp import web
from telegram import Update
from telegram.constants import ChatAction
from dotenv import load_dotenv
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters
)
from handlers import (
    start_handler, status_command, id_command, help_command,
    list_routes_command, add_routes_command, delete_routes_command,
    list_senders_command, clear_senders_command,
    get_weekly_summary_command, feedback_command,
    forward_homework, reload_config, clear_homework_log
)

# --- Load config --- #
load_dotenv()

ADMIN_CHAT_IDS=os.getenv("ADMIN_CHAT_IDS")
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook")
PORT = int(os.getenv("PORT", 10000))

# Admins
ADMIN_CHAT_IDS = list(map(int, os.getenv("ADMIN_CHAT_IDS", "").split(","))) if os.getenv("ADMIN_CHAT_IDS") else []
logging.info(f"Admin IDs loaded: {ADMIN_CHAT_IDS}")

# Routes
ROUTES_MAP = {}
if raw_routes := os.getenv("ROUTES_MAP", "").strip():
    try:
        ROUTES_MAP = {
            int(k): int(v)
            for route in raw_routes.split(",")
            for k, v in [route.split(":")]
        }
    except ValueError as e:
        logging.error(f"Invalid ROUTES_MAP: {e}")

# --- Shared Bot Instance --- #
application = ApplicationBuilder().token(BOT_TOKEN).build()

# Inject shared data (before handlers)
application.bot_data.update({
    "ROUTES_MAP": ROUTES_MAP,
    "ADMIN_CHAT_IDS": ADMIN_CHAT_IDS,
    "FORWARDED_LOGS": [],
    "SENDER_ACTIVITY": {}
})

# Filters
admin_filter = filters.User(ADMIN_CHAT_IDS)

# Register command handlers
application.add_handlers([
    CommandHandler("start", start_handler),
    CommandHandler("help", help_command),
    CommandHandler("id", id_command),
    CommandHandler("status", status_command),
    CommandHandler("feedback", feedback_command),

    # Admin commands
    CommandHandler("list_routes", list_routes_command, admin_filter),
    CommandHandler("add_routes", add_routes_command, admin_filter),
    CommandHandler("delete_routes", delete_routes_command, admin_filter),
    CommandHandler("reload_config", reload_config, admin_filter),
    CommandHandler("get_weekly_summary", get_weekly_summary_command, admin_filter),
    CommandHandler("clear_homework_log", clear_homework_log, admin_filter),
    CommandHandler("list_senders", list_senders_command, admin_filter),
    CommandHandler("clear_sender_data", clear_senders_command, admin_filter),

    # Fallback handler for media/text
    MessageHandler(filters.ALL, forward_homework)
])

# Webhook receiver
async def on_webhook(request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return web.Response()

raw_map = os.getenv("ROUTES_MAP", "")
route_map = {
    int(src.strip()): int(dst.strip())
    for pair in raw_map.split(",") if ":" in pair
    for src, dst in [pair.split(":")]
}
application.bot_data["ROUTE_MAP"] = route_map
logging.info(f"📦 Loaded {len(route_map)} active route(s).")


# Webhook setup
async def setup_webhook():
    try:
        await application.bot.set_webhook(
            url=f"{WEBHOOK_URL}{WEBHOOK_PATH}",
            allowed_updates=Update.ALL_TYPES
        )
        logging.info("✅ Bot initialized and webhook set successfully.")

        # Notify all admins on startup with live route count
        try:
            route_map = application.bot_data.get("ROUTE_MAP", {})
            active_routes = len(route_map)

            for admin_id in ADMIN_CHAT_IDS:
                try:
                    await application.bot.send_message(
                        chat_id=admin_id,
                        text=(
                            f"🤖 Bot restarted.\n"
                            f"🗺️ Active Routes: {active_routes} source-to-target mappings\n"
                            f"🌐 Webhook URL: `{WEBHOOK_URL}`"
                        ),
                        parse_mode="Markdown"
                    )
                except Exception as e:
                    logger.warning(f"⚠️ Could not notify admin {admin_id}: {e}")

        except Exception as e:
            logging.warning(f"⚠️ Failed to notify admins: {e}")

    except Exception as e:
        logging.error(f"❌ Webhook setup failed: {e}")


# Main runner
async def main():
    await setup_webhook()

    aio_app = web.Application()
    aio_app.router.add_post(WEBHOOK_PATH, on_webhook)

    # Optional health check
    async def health_check(request):
        return web.Response(text="OK")

    aio_app.router.add_get("/health", health_check)

    runner = web.AppRunner(aio_app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()

    logging.info(f"🚀 Server running on port {PORT}")
    await asyncio.Event().wait()

# Entrypoint
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    asyncio.run(main())
