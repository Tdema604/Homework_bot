import logging
from telegram import Update
from telegram.ext import ContextTypes
from utils import is_homework, get_route_map

logger = logging.getLogger(__name__)

# Load ROUTE_MAP once at startup
ROUTE_MAP = get_route_map()

# /id command to check group or user chat ID
async def chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    await update.message.reply_text(f"🆔 Chat ID: `{chat.id}`", parse_mode='Markdown')

# /start command to greet users
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info(f"📥 /start command from {user.username or user.id}")
    await update.message.reply_text("👋 Hello! I'm your Homework Forwarder Bot. Drop homework, and I’ll pass it along!")

# Main message forwarding logic
async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        message = update.message
        if not message:
            logger.warning("⚠️ Update has no message content.")
            return

        source_id = message.chat_id
        target_id = ROUTE_MAP.get(source_id)
        admin_id = context.bot_data.get("ADMIN_CHAT_ID")

        if not target_id:
            logger.warning(f"⛔ No target mapped for source chat ID: {source_id}")
            return

        # Filter spam and irrelevant content
        if message.text and not is_homework(message):
            logger.info(f"🚫 Ignored non-homework message: {message.text}")
            return

        caption = message.caption or ""
        media_type = "Unknown"

        if message.text:
            media_type = "Text"
            await context.bot.send_message(chat_id=target_id, text=message.text)
        elif message.photo:
            media_type = "Photo"
            await context.bot.send_photo(chat_id=target_id, photo=message.photo[-1].file_id, caption=caption)
        elif message.video:
            media_type = "Video"
            await context.bot.send_video(chat_id=target_id, video=message.video.file_id, caption=caption)
        elif message.document:
            media_type = "Document"
            await context.bot.send_document(chat_id=target_id, document=message.document.file_id, caption=caption)
        elif message.audio:
            media_type = "Audio"
            await context.bot.send_audio(chat_id=target_id, audio=message.audio.file_id, caption=caption)
        elif message.voice:
            media_type = "Voice"
            await context.bot.send_voice(chat_id=target_id, voice=message.voice.file_id)
        else:
            logger.warning(f"⚠️ Unsupported message type received: {message}")
            return

        logger.info(f"✅ Forwarded {media_type} from {source_id} to {target_id}.")

        sender = update.effective_user
        sender_name = f"@{sender.username}" if sender.username else f"user {sender.id}"

        await context.bot.send_message(
            chat_id=admin_id,
            text=f"📤 Forwarded {media_type} from {sender_name} (chat ID: {source_id})."
        )

    except Exception as e:
        logger.exception(f"🚨 Exception while forwarding message: {e}")
