from aiohttp import web
import logging
from telegram import Update

logger = logging.getLogger(__name__)

def setup_routes(app, bot, application):
    async def handle_webhook(request):
        try:
            data = await request.json()
            update = Update.de_json(data, bot)
            await application.process_update(update)
            return web.Response(text="OK")
        except Exception as e:
            logger.error(f"Webhook error: {e}")
            return web.Response(status=500, text="Webhook error")

    async def healthcheck(request):
        return web.Response(text="Bot is alive!")

    app.router.add_post("/webhook", handle_webhook)
    app.router.add_get("/", healthcheck)
    logger.info("🔌 Web routes set up successfully.")
