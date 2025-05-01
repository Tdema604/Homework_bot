import logging
from telegram import Update
from telegram.ext import CallbackContext

logger = logging.getLogger(__name__)

# Start command handler
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Hi! I'm your Homework Forwarder Bot.")
    logger.info(f"Start command received from {update.effective_user.id}")

# Forwarding the message (text, media, etc.)
async def forward_message(update: Update, context: CallbackContext):
    try:
        message = update.message
        if not message:
            logger.warning("No message found in update!")
            return

        target_id = context.bot_data["TARGET_CHAT_ID"]
        admin_id = context.bot_data["ADMIN_CHAT_ID"]

        # Log message type for debugging
        if message.text:
            media_type = "Text"
            await context.bot.send_message(chat_id=target_id, text=message.text)
        elif message.photo:
            media_type = "Photo"
            await context.bot.send_photo(chat_id=target_id, photo=message.photo[-1].file_id)
        elif message.video:
            media_type = "Video"
            await context.bot.send_video(chat_id=target_id, video=message.video.file_id)
        elif message.document:
            media_type = "Document"
            await context.bot.send_document(chat_id=target_id, document=message.document.file_id)
        elif message.audio:
            media_type = "Audio"
            await context.bot.send_audio(chat_id=target_id, audio=message.audio.file_id)
        elif message.voice:
            media_type = "Voice"
            await context.bot.send_voice(chat_id=target_id, voice=message.voice.file_id)
        else:
            # Catch unsupported formats
            logger.warning(f"Unsupported media type received: {message}")
            return

        # Log the forwarded media type for debugging
        logger.info(f"Forwarded {media_type} message successfully.")

        # Notify Admin after successful forwarding
        user = update.effective_user
        await context.bot.send_message(
            chat_id=admin_id,
            text=f"✅ Message forwarded from @{user.username or user.id} ({media_type})."
        )

    except Exception as e:
        logger.error(f"Error forwarding message: {e}")
