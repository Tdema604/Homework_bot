import logging
from telegram import Update
from telegram.ext import ContextTypes
from utils import is_homework, get_route_map

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! I'm your Homework Forwarder Bot.\nUse /status to check my current config.")

async def chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Chat ID: {update.effective_chat.id}", parse_mode="Markdown")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = context.bot_data.get("ADMIN_CHAT_ID")
    route_map = context.bot_data.get("ROUTE_MAP", {})
    allowed = context.bot_data.get("ALLOWED_SOURCE_CHAT_IDS", [])
    status_text = (
        f"Admin ID: {admin_id}\n"
        f"Allowed Sources: {allowed}\n"
        f"Active Routes: {len(route_map)}\n\n"
        + "\n".join([f"{k} → {v}" for k, v in route_map.items()])
    )
    await update.message.reply_text(status_text)

async def reload_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.bot_data["ROUTE_MAP"] = get_route_map()
    await update.message.reply_text("ROUTE_MAP reloaded from .env!")

async def add_route(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        return await update.message.reply_text("Usage: /addroute <source_chat_id> <target_chat_id>")

    try:
        source = int(context.args[0])
        target = int(context.args[1])
        context.bot_data.setdefault("ROUTE_MAP", {})[source] = target
        await update.message.reply_text(f"✅ Route added: {source} → {target}")
    except ValueError:
        await update.message.reply_text("Invalid chat IDs. They must be integers.")

async def remove_route(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        return await update.message.reply_text("Usage: /removeroute <source_chat_id>")

    try:
        source = int(context.args[0])
        if context.bot_data.get("ROUTE_MAP", {}).pop(source, None) is not None:
            await update.message.reply_text(f"❌ Route removed for source: {source}")
        else:
            await update.message.reply_text(f"No route found for source: {source}")
    except ValueError:
        await update.message.reply_text("Invalid chat ID.")

async def list_routes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    route_map = context.bot_data.get("ROUTE_MAP", {})
    if not route_map:
        await update.message.reply_text("No routes configured.")
    else:
        msg = "\n".join([f"{src} → {dst}" for src, dst in route_map.items()])
        await update.message.reply_text(f"Active Routes:\n{msg}")

# Main message forwarding logic
async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = update.message
        if not message:
            logger.warning(" No message found.")
            return

        source_id = message.chat_id
        target_id = ROUTE_MAP.get(source_id)
        admin_id = context.bot_data.get("ADMIN_CHAT_ID")

        if not target_id:
            logger.warning(f" No target mapped for source chat ID: {source_id}")
            return

        if message.text and not is_homework(message):
            logger.info(f" Ignored non-homework message: {message.text}")
            return

        caption = message.caption or ""
        sender = update.effective_user
        sender_name = f"@{sender.username}" if sender.username else f"user {sender.id}"

        media_type = None

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
            logger.warning(f" Unsupported message type: {message}")
            return

        logger.info(f" Forwarded {media_type} from {source_id} to {target_id}.")

        # Notify admin
        await context.bot.send_message(
            chat_id=admin_id,
            text=f" Forwarded {media_type} from {sender_name} (chat ID: {source_id})."
        )

    except Exception as e:
        logger.exception(f" Exception while forwarding message: {e}")