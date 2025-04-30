import logging
from aiohttp import web
from telegram import Bot
from telegram.ext import Application
from utils import is_spam, forward_homework, notify_admin

logger = logging.getLogger(__name__)

# This function sets up routes for both webhook and health check
def setup_routes(app, bot=None, application=None):
    # Health check route for webhook to ensure the server is up
    async def health(request):
        return web.Response(text="OK")

    # Webhook endpoint to receive updates
    async def webhook(request):
        json_str = await request.json()
        update = telegram.Update.de_json(json_str, bot)
        application.process_update(update)
        return web.Response()

    # Add routes to the aiohttp app
    app.router.add_get("/health", health)  # Health check
    app.router.add_post("/webhook", webhook)  # Webhook listener

    logger.info("🔌 Web routes set up successfully.")

