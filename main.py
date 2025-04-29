# main.py

import asyncio
import logging
import time
from waitress import serve
from utils import notify_admin_startup, set_webhook
from web import app
from datetime import datetime

# Log config
logging.basicConfig(level=logging.INFO)

# Track uptime
start_time = time.time()

async def startup():
    await set_webhook()
    await notify_admin_startup()

if __name__ == "__main__":
    try:
        asyncio.run(startup())
    except RuntimeError as e:
        logging.error(f"Startup error: {e}")

    logging.info("Serving via Waitress...")
    serve(app, host="0.0.0.0", port=8080)
