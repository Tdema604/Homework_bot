from aiohttp import web
import logging
from telegram import Update
from telegram.ext import Application

logger = logging.getLogger(__name__)

def setup_routes(app: web.Application, bot, telegram_app: Application):
    # Webhook route
    async def handle_webhook(request):
        try:
            data = await request.json()
            logger.info(f"📡 Webhook request from IP: {request.remote}")
            logger.info(f"📨 Webhook data: {data}")

            update = Update.de_json(data, bot)
            await telegram_app.process_update(update)

            return web.Response(status=200)
        except Exception as e:
            logger.error(f"🔥 Webhook error: {e}")
            return web.Response(status=500, text="Webhook processing failed")

    # Health check route
    async def health_check(request):
        return web.Response(text="✅ Bot is healthy", status=200)

    app.router.add_post("/", handle_webhook)
    app.router.add_get("/", health_check)

    logger.info("✅ Routes registered for '/'")
