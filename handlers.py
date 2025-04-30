import logging
from telegram import Update
from telegram.ext import Application

logger = logging.getLogger(__name__)

async def webhook(request):
    try:
        # Get JSON payload from the webhook request
        json_str = await request.json()
        logger.info(f"Received webhook data: {json_str}")  # Log the payload for debugging

        # Process the update
        update = Update.de_json(json_str, bot)
        application.process_update(update)  # Pass the update to the application

        return web.Response()  # Return a successful response
    except Exception as e:
        logger.error(f"Error while processing webhook: {e}")  # Log the error
        return web.Response(status=500, text=f"Internal Server Error: {e}")  # Return error response
