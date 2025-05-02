import logging
from telegram import Update
from telegram.ext import ContextTypes
from utils import is_homework, get_route_map
from utils import load_env  # at the top if not already

logger = logging.getLogger(name)

# Load routing map once on module load
ROUTE_MAP = get_route_map()

# /id command: show the chat ID
async def chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    await update.message.reply_text(f"🆔 Chat ID: {chat.id}", parse_mode='Markdown')

# /start command: intro message
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info(f"📥 /start command from {user.username or user.id}")
    await update.message.reply_text(
        "👋 Hello! I'm your Homework Forwarder Bot. Just drop your homework, and I’ll forward it to the parents' group!"
    )

# Core forwarding logic
async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        message = update.message
        if not message:
            logger.warning("⚠️ No message found in update.")
            return

        source_id = message.chat_id
        target_id = ROUTE_MAP.get(source_id)
        admin_id = context.bot_data.get("ADMIN_CHAT_ID")

        if not target_id:
            logger.warning(f"⛔ No target mapped for source chat ID: {source_id}")
            return

        # Filter spam/non-homework
        if message.text and not is_homework(message):
            logger.info(f"🚫 Ignored non-homework message: {message.text}")
            return

        # Handle different message types
        caption = message.caption or ""
        sender = update.effective_user
        sender_name = f"@{sender.username}" if sender.username else f"user {sender.id}"

        # Send message accordingly
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
            logger.warning(f"⚠️ Unsupported message type received: {message}")
            return

        logger.info(f"✅ Forwarded {media_type} from {source_id} to {target_id}.")
# /status command to report health
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"📥 /status command from {user.username or user.id}")
    
    status_msg = (
        "✅ *Bot Status*\n"
        f"• Uptime: always-on (webhook)\n"
        f"• Active Routes: {len(ROUTE_MAP)} source-to-target mappings\n"
        f"• Admin Chat ID: {context.bot_data.get('ADMIN_CHAT_ID')}"
    )

    await update.message.reply_text(status_msg, parse_mode="Markdown")
# /reload command
async def reload_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    admin_id = context.bot_data.get("ADMIN_CHAT_ID")
    if user.id != admin_id:
        await update.message.reply_text("⛔ Access denied. Only the admin can reload config.")
        return

    try:
        load_env()
        global ROUTE_MAP
        ROUTE_MAP = get_route_map()
        logger.info("♻️ Environment and route map reloaded.")
        await update.message.reply_text("♻️ Config reloaded. New routes applied.")
    except Exception as e:
        logger.exception("🚨 Failed to reload config:")
        await update.message.reply_text("❌ Failed to reload config.")

        # Notify admin
        await context.bot.send_message(
            chat_id=admin_id,
            text=f"📤 Forwarded {media_type} from {sender_name} (chat ID: {source_id})."
        )

    except Exception as e:
        logger.exception(f"🚨 Error during message forwarding: {e}")