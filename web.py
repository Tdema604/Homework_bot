from aiohttp import web
from telegram import Update
import logging
from utils import is_telegram_request  # Make sure this is implemented

logger = logging.getLogger(__name__)

def setup_routes(app, bot, application):
    async def handle_webhook(request):
        client_ip = request.headers.get('X-Real-IP', request.remote)
        logger.info(f"Received webhook request from IP: {client_ip}")

        if not is_telegram_request(client_ip):
            logger.error(f"❌ Forbidden request from: {client_ip}")
            return web.Response(status=403, text="Forbidden: Invalid source")

        try:
            data = await request.json()
            logger.info(f"📨 Webhook data: {data}")

            update = Update.de_json(data, bot)
            await application.process_update(update)

            return web.Response(text="OK", content_type='application/json')
        except Exception as e:
            logger.error(f"🔥 Webhook error: {e}")
            return web.Response(status=500, text="Webhook error")

    async def healthcheck(request):
        return web.Response(text="Bot is alive!")

    app.router.add_post("/", handle_webhook)
    app.router.add_get("/", healthcheck)
    logger.info("🔌 Web routes set up successfully.")
