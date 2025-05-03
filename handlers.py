import os
import logging
from aiohttp import web
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from dotenv import load_dotenv
from handlers import forward_message, start, chat_id, status, reload_config
from web import setup_routes
from utils import get_route_map

# Logging setup
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)  # Fixed: use name

# Load environment variables
load_dotenv()

# Required .env vars
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
ALLOWED_SOURCE_CHAT_IDS = os.getenv("SOURCE_CHAT_IDS", "").split(",")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0") or "0")
PORT = int(os.getenv("PORT", 10000))  # Default port for Render

# Validation
if not TOKEN or not WEBHOOK_URL:
    raise ValueError("Missing BOT_TOKEN or WEBHOOK_URL in .env")

# Create aiohttp web server
app = web.Application()

# On startup
async def on_startup(app):
    application = Application.builder().token(TOKEN).build()

    # Shared bot data
    application.bot_data["ALLOWED_SOURCE_CHAT_IDS"] = [int(id.strip()) for id in ALLOWED_SOURCE_CHAT_IDS if id.strip()]
    application.bot_data["ADMIN_CHAT_ID"] = ADMIN_CHAT_ID

    # Telegram command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("id", chat_id))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("reload", reload_config))

    # Message forwarding handler
    application.add_handler(MessageHandler(filters.ALL, forward_message))

    # Initialize app and set webhook
    await application.initialize()
    await application.bot.set_webhook(url=WEBHOOK_URL)
    setup_routes(app, application.bot, application)
import logging
from telegram import Update
from telegram.ext import ContextTypes
from utils import is_homework, get_route_map, load_env

logger = logging.getLogger(name)  # Fixed

# /id command
async def chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    await update.message.reply_text(f"Chat ID: {chat.id}", parse_mode='Markdown')

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"/start from {user.username or user.id}")
    await update.message.reply_text("Hello! I'm your Homework Forwarder Bot. Drop homework, and I'll pass it along!")

# /status command
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"/status from {user.username or user.id}")

    route_map = context.bot_data.get("ROUTE_MAP", {})
    admin_id = context.bot_data.get("ADMIN_CHAT_ID")

    status_msg = (
        "*Bot Status*\n"
        f"Uptime: always-on (webhook)\n"
        f"Active Routes: {len(route_map)} source-to-target mappings\n"
        f"Admin Chat ID: {admin_id}"
    )

    await update.message.reply_text(status_msg, parse_mode="Markdown")

# /reload command
async def reload_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    admin_id = context.bot_data.get("ADMIN_CHAT_ID")

    if user.id != admin_id:
        await update.message.reply_text("Access denied. Only the admin can reload config.")
        return

    try:
        load_env()
        context.bot_data["ROUTE_MAP"] = get_route_map()  # Fix added here
        logger.info("Config and routes reloaded.")
        await update.message.reply_text("Config reloaded. New routes applied.")
    except Exception as e:
        logger.exception("Failed to reload config:")
        await update.message.reply_text("Failed to reload config.")

# Forwarding logic
async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = update.message
        if not message:
            logger.warning("No message found.")
            return

        source_id = message.chat_id
        route_map = context.bot_data.get("ROUTE_MAP", {})  # Fixed
        target_id = route_map.get(source_id)
        admin_id = context.bot_data.get("ADMIN_CHAT_ID")

        if not target_id:
            logger.warning(f"No target mapped for source chat ID: {source_id}")
            return

        if message.text and not is_homework(message):
            logger.info(f"Ignored non-homework message: {message.text}")
            return

        caption = message.caption or ""
        sender = update.effective_user
        sender_name = f"@{sender.username}" if sender.username else f"user {sender.id}"

        if message.text:
            await context.bot.send_message(chat_id=target_id, text=message.text)
            media_type = "Text"
        elif message.photo:
            await context.bot.send_photo(chat_id=target_id, photo=message.photo[-1].file_id, caption=caption)
            media_type = "Photo"
        elif message.video:
            await context.bot.send_video(chat_id=target_id, video=message.video.file_id, caption=caption)
            media_type = "Video"
        elif message.document:
            await context.bot.send_document(chat_id=target_id, document=message.document.file_id, caption=caption)
            media_type = "Document"
        elif message.audio:
            await context.bot.send_audio(chat_id=target_id, audio=message.audio.file_id, caption=caption)
            media_type = "Audio"
        elif message.voice:
            await context.bot.send_voice(chat_id=target_id, voice=message.voice.file_id)
            media_type = "Voice"
        else:
            logger.warning(f"Unsupported message type: {message}")
            return

        logger.info(f"Forwarded {media_type} from {source_id} to {target_id}.")

await context.bot.send_message(
            chat_id=admin_id,
            text=f"Forwarded {media_type} from {sender_name} (chat ID: {source_id})."
        )

    except Exception as e:
        logger.exception(f"Exception while forwarding message: {e}")