from aiohttp import web
from telegram import Update
import logging

logger = logging.getLogger(__name__)

def is_telegram_request(ip):
    # For now, bypass actual IP check logic
    return True

def setup_routes(app, bot, application):
    async def handle_webhook(request):
        client_ip = request.headers.get('X-Real-IP', request.remote)
        logger.info(f"🌐 Received webhook request from IP: {client_ip}")

        if not is_telegram_request(client_ip):
            logger.warning(f"⚠️ Unauthorized request source: {client_ip}")
            return web.Response(status=403, text="Forbidden: Invalid source")

        try:
            data = await request.json()
            logger.info(f"📨 Webhook data: {data}")

            update = Update.de_json(data, bot)
            await application.process_update(update)

            return web.Response(text="OK", content_type='application/json')
        except Exception as e:
            logger.error(f"🔥 Webhook processing error: {e}")
            return web.Response(status=500, text="Webhook error")

    async def healthcheck(request):
        return web.Response(text="✅ Bot is alive and kicking!")

    # Register routes
    app.router.add_post("/", handle_webhook)
    app.router.add_get("/", healthcheck)
    logger.info("🔌 Web routes set up successfully.")
