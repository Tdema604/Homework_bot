from aiohttp import web

def setup_routes(application):
    """Sets up /webhook and /health endpoints on the Telegram Application."""
    async def webhook_handler(request):
        """Handles incoming Telegram updates from the webhook."""
        data = await request.json()
        await application.update_queue.put(data)
        return web.Response(text="OK")

    async def health_check(request):
        """Health check endpoint for uptime monitoring."""
        return web.Response(text="Bot is healthy!")

    application.web_app.add_routes([
        web.post("/webhook", webhook_handler),
        web.get("/health", health_check),
    ])
