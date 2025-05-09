import logging
import os
import asyncio
from aiohttp import web
from dotenv import load_dotenv
from telegram import Update
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

# --- Configuration --- #
load_dotenv()

# Environment Variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook")
PORT = int(os.getenv("PORT", 10000))  # For Render.com

# Admin Setup
ADMIN_CHAT_IDS = list(map(int, os.getenv("ADMIN_CHAT_IDS", "").split(","))) if os.getenv("ADMIN_CHAT_IDS") else []
logging.info(f"Admin IDs loaded: {ADMIN_CHAT_IDS}")

# Routes Mapping
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

# --- Bot Setup --- #
application = ApplicationBuilder().token(BOT_TOKEN).build()

# Inject shared data (MUST happen before handlers)
application.bot_data.update({
    "ROUTES_MAP": ROUTES_MAP,
    "ADMIN_CHAT_IDS": ADMIN_CHAT_IDS,
    "FORWARDED_LOGS": [],
    "SENDER_ACTIVITY": {}
})

# --- Handlers --- #
# Admin-only commands (with user filter)
admin_filter = filters.User(ADMIN_CHAT_IDS)
application.add_handlers([
    CommandHandler("start", start_handler),
    CommandHandler("help", help_command),
    CommandHandler("id", id_command),
    CommandHandler("status", status_command),
    CommandHandler("list_routes", list_routes_command, admin_filter),
    CommandHandler("add_routes", add_routes_command, admin_filter),
    CommandHandler("delete_routes", delete_routes_command, admin_filter),
    CommandHandler("feedback", feedback_command),
    CommandHandler("reload_config", reload_config, admin_filter),
    CommandHandler("get_weekly_summary", get_weekly_summary_command, admin_filter),
    CommandHandler("list_senders", list_senders_command, admin_filter),
    CommandHandler("clear_sender_data", clear_senders_command, admin_filter),
    
    # Unified message handler
    MessageHandler(filters.ALL, handle_message)
])

# --- Webhook Server --- #
async def webhook_handler(request):
    json_data = await request.json()
    update = Update.de_json(json_data, application.bot)
    await application.process_update(update)
    return web.Response()

async def setup_webhook():
    """Configure webhook and notify admins."""
    try:
        await application.bot.set_webhook(
            url=f"{WEBHOOK_URL}{WEBHOOK_PATH}",
            allowed_updates=Update.ALL_TYPES
        )
        logging.info(f"Webhook set to: {WEBHOOK_URL}{WEBHOOK_PATH}")
        
        # Notify admins
        for admin_id in ADMIN_CHAT_IDS:
            try:
                await application.bot.send_message(admin_id, "🤖 Bot started successfully!")
            except Exception as e:
                logging.error(f"Failed to notify admin {admin_id}: {e}")
    except Exception as e:
        logging.critical(f"Webhook setup failed: {e}")
        raise

async def main():
    await setup_webhook()
    
    # Start aiohttp server
    server = web.Application()
    server.router.add_post(WEBHOOK_PATH, webhook_handler)
    
    runner = web.AppRunner(server)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    
    logging.info(f"Server running on port {PORT}")
    await asyncio.Event().wait()  # Run forever

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    asyncio.run(main())
