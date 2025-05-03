from aiohttp import web
import logging
from telegram import Update
from telegram.ext import Application

logger = logging.getLogger(__name__)

def setup_routes(app: web.Application, bot, telegram_app: Application):
    # Webhook POST handler
    async def handle_webhook(request):
        try:
            data = await request.json()
            logger.info(f"Webhook request from IP: {request.remote}")
            logger.debug(f"Webhook data: {data}")

            update = Update.de_json(data, bot)
            await telegram_app.process_update(update)

            return web.Response(status=200, text="OK")

        except Exception as e:
            logger.exception("Error handling webhook:")
            return web.Response(status=500, text="Webhook processing failed")

    # Simple GET health check
    async def health_check(request):
        return web.Response(text="Bot is alive & well", status=200)

    # Register the routes
    app.router.add_post("/", handle_webhook)
    app.router.add_get("/", health_check)

    logger.info("Webhook and health routes registered.")