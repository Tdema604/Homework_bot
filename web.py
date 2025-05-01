from aiohttp import web
from telegram import Update  # ✅ Proper import
import logging
import ipaddress
import requests

logger = logging.getLogger(__name__)

# Telegram IPs range for verification
TELEGRAM_IP_RANGES = [
    ipaddress.ip_network("149.154.160.0/22"),
    ipaddress.ip_network("149.154.164.0/22"),
    ipaddress.ip_network("149.154.168.0/22"),
    ipaddress.ip_network("149.154.172.0/22")
]

# Function to verify if the request is from Telegram's servers
def is_telegram_request(request_ip):
    try:
        # Check if the request's IP address is within Telegram's IP range
        ip = ipaddress.ip_address(request_ip)
        for network in TELEGRAM_IP_RANGES:
            if ip in network:
                return True
        return False
    except ValueError:
        return False

def setup_routes(app, bot, application):
    async def handle_webhook(request):
        try:
            # Verify the source IP (ensure it's Telegram's server)
            client_ip = request.headers.get('X-Real-IP', request.remote)
            if not is_telegram_request(client_ip):
                logger.error(f"Invalid request source: {client_ip}")
                return web.Response(status=403, text="Forbidden: Invalid source")

            data = await request.json()
            update = Update.de_json(data, bot)  # ✅ Correct usage
            await application.process_update(update)
            return web.Response(text="OK", content_type='application/json')
        
        except Exception as e:
            logger.error(f"Webhook error: {e}")
            return web.Response(status=500, text="Internal Server Error")

    async def healthcheck(request):
        return web.Response(text="Bot is alive!", content_type='text/plain')

    # Accept POST on root (Render uses this), and GET for health check
    app.router.add_post("/", handle_webhook)
    app.router.add_get("/", healthcheck)

    logger.info("🔌 Web routes set up successfully.")
