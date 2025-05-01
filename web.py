from aiohttp import web
from telegram import Update
import logging

logger = logging.getLogger(__name__)

def setup_routes(app, bot, application):
    async def handle_webhook(request):
        client_ip = request.headers.get('X-Real-IP', request.remote)
        logger.info(f"📡 Incoming webhook request from IP: {client_ip}")

        # 🚫 TEMP: Disable IP validation for now
        if not is_telegram_request(client_ip):
    logger.error(f"🚫 Invalid request source: {client_ip}")
    return web.Response(status=403, text="Forbidden: Invalid source")

        try:
            data = await request.json()
            logger.info(f"📨 Webhook JSON: {data}")
            update = Update.de_json(data, bot)
            await application.process_update(update)
            return web.Response(text="OK", content_type='application/json')
        except Exception as e:
            logger.error(f"🔥 Error while handling webhook: {e}")
            return web.Response(status=500, text="Internal Server Error")

    async def healthcheck(request):
        return web.Response(text="Bot is alive!")

    app.router.add_post("/", handle_webhook)
    app.router.add_get("/", healthcheck)
    logger.info("✅ Routes registered on '/'")
