import logging
from telegram import Update
from telegram.ext import ContextTypes
from utils import is_homework, get_route_map

logger = logging.getLogger(__name__)
ROUTE_MAP = get_route_map()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("👋 Hello! I'm your Homework Forwarder Bot. Drop homework, and I’ll pass it along!")
    logger.info(f"📥 /start command from {update.effective_user.id}")

async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        message = update.message
        if not message:
            logger.warning("⚠️ No message found in update.")
            return

        logger.info(f"📥 Incoming message detected: {message}")

        source_id = message.chat_id
        target_id = ROUTE_MAP.get(source_id)
        admin_id = context.bot_data.get("ADMIN_CHAT_ID")

        if not target_id:
            logger.warning(f"⛔ No target mapped for source chat ID: {source_id}")
            return

        # Filter non-homework
        if message.text and not is_homework(message):
            logger.info(f"📌 Ignored non-homework message: {message.text}")
            return

        media_type = "Unknown"
        caption = message.caption or ""

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
            logger.warning(f"⛔ Unsupported message type: {message}")
            return

        logger.info(f"✅ Forwarded {media_type} from {source_id} to {target_id}.")

        sender = update.effective_user
        await context.bot.send_message(
            chat_id=admin_id,
            text=f"📤 Forwarded {media_type} from @{sender.username or sender.id} (chat {source_id})."
        )

    except Exception as e:
        logger.error(f"🚨 Error while forwarding: {e}")
