import logging
from telegram import Update, Bot, Message
from telegram.ext import CallbackContext
import telegram
from aiohttp import web
from telegram.ext import Application

logger = logging.getLogger(__name__)

# Webhook handler
async def webhook(request, bot, application):
    try:
        json_str = await request.json()
        update = telegram.Update.de_json(json_str, bot)
        application.process_update(update)
        return web.Response()  # Return success response
    except Exception as e:
        logger.error(f"Error while processing webhook: {e}")
        return web.Response(status=500, text=f"Internal Server Error: {e}")


# Forward message handler
async def forward_message(update: Update, context: CallbackContext):
    try:
        # Retrieve the incoming message
        message = update.message

        if not message:
            logger.warning("No message found in the update!")
            return

        # Check if the TARGET_CHAT_ID is set
        if "TARGET_CHAT_ID" not in context.bot_data:
            logger.error("TARGET_CHAT_ID is not set in bot data.")
            return

        # Forward text message
        if message.text:
            await context.bot.send_message(chat_id=context.bot_data["TARGET_CHAT_ID"], text=message.text)
            logger.info(f"Forwarded text message: {message.text}")

        # Forward media (photo, video, etc.)
        elif message.photo:
            await context.bot.send_photo(chat_id=context.bot_data["TARGET_CHAT_ID"], photo=message.photo[-1].file_id)
            logger.info("Forwarded photo message.")

        elif message.video:
            await context.bot.send_video(chat_id=context.bot_data["TARGET_CHAT_ID"], video=message.video.file_id)
            logger.info("Forwarded video message.")

        # Forward audio message
        elif message.audio:
            await context.bot.send_audio(chat_id=context.bot_data["TARGET_CHAT_ID"], audio=message.audio.file_id)
            logger.info("Forwarded audio message.")

        # Forward document (PDF, etc.)
        elif message.document:
            await context.bot.send_document(chat_id=context.bot_data["TARGET_CHAT_ID"], document=message.document.file_id)
            logger.info("Forwarded document message.")

        # Forward voice note
        elif message.voice:
            await context.bot.send_voice(chat_id=context.bot_data["TARGET_CHAT_ID"], voice=message.voice.file_id)
            logger.info("Forwarded voice note message.")

    except Exception as e:
        logger.error(f"Error in forwarding message: {e}")
