import logging
from telegram import Update
import json

logger = logging.getLogger(__name__)

async def webhook(request):
    try:
        # Log the incoming request for debugging
        json_str = await request.json()
        logger.info(f"Received webhook data: {json.dumps(json_str)}")

        # Convert the incoming JSON data to a telegram update
        update = Update.de_json(json_str, bot)

        # Process the update (handle the message, etc.)
        application.process_update(update)

        return web.Response()

    except Exception as e:
        logger.error(f"Error processing webhook request: {e}")
        return web.Response(status=500, text="Internal Server Error")
