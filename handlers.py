from telegram import Update, Bot, Message
from telegram.ext import CallbackContext
import logging

logger = logging.getLogger(__name__)

async def forward_message(update: Update, context: CallbackContext):
    try:
        # Retrieve the incoming message
        message = update.message

        if not message:
            logger.warning("No message found in the update!")
            return

        # Forward text message
        if message.text:
            # Forward text message to the target chat
            await context.bot.send_message(chat_id=context.bot_data["TARGET_CHAT_ID"], text=message.text)
            logger.info(f"Forwarded text message: {message.text}")

        # Forward media (photo, video, etc.)
        elif message.photo:
            # Forward photo to the target chat
            await context.bot.send_photo(chat_id=context.bot_data["TARGET_CHAT_ID"], photo=message.photo[-1].file_id)
            logger.info("Forwarded photo message.")

        elif message.video:
            # Forward video to the target chat
            await context.bot.send_video(chat_id=context.bot_data["TARGET_CHAT_ID"], video=message.video.file_id)
            logger.info("Forwarded video message.")

        # Handle other types (audio, documents, etc.) as needed
        # You can add similar blocks for other message types like document, voice, etc.

    except Exception as e:
        logger.error(f"Error in forwarding message: {e}")
