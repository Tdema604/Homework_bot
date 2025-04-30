from aiohttp import web
import logging

logger = logging.getLogger(__name__)

# Set up routes for webhook and health check
def setup_routes(app, bot, application):
    # Handle incoming webhook requests
    async def handle_webhook(request):
        try:
            data = await request.json()
            update = application.bot._telegram.Update.de_json(data, bot)
            await application.process_update(update)
            return web.Response(text="OK")
        except Exception as e:
            logger.error(f"Webhook error: {e}")
            return web.Response(status=500, text="Internal Server Error")

    # Health check route
    async def healthcheck(request):
        return web.Response(text="Bot is alive!")

    # Add routes to aiohttp application
    app.router.add_post("/", handle_webhook)
    app.router.add_get("/", healthcheck)
    logger.info("🔌 Web routes set up successfully.")
