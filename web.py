import logging
import telegram
from aiohttp import web
from telegram import Bot
from telegram.ext import Application

logger = logging.getLogger(__name__)

# This function sets up routes for both webhook and health check
def setup_routes(app, bot=None, application=None):
    # Health check route for webhook to ensure the server is up
    async def health(request):
        return web.Response(text="OK")

    # Webhook endpoint to receive updates
    async def webhook(request):
        try:
            json_str = await request.json()
            update = telegram.Update.de_json(json_str, bot)
            application.process_update(update)
            return web.Response()  # return success response
        except Exception as e:
            logger.error(f"Error while processing webhook: {e}")
            return web.Response(status=500, text=f"Internal Server Error: {e}")

    # Root route (to prevent 404 errors for root endpoint)
    async def root(request):
        return web.Response(text="Welcome to the Homework Bot! Use /health for status.")

    # Add routes to the aiohttp app
    app.router.add_get("/", root)  # Add root handler
    app.router.add_get("/health", health)  # Health check
    app.router.add_post("/webhook", webhook)  # Webhook listener

    logger.info("🔌 Web routes set up successfully.")
