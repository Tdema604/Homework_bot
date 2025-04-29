import os
import logging
from telegram.ext import ApplicationBuilder
from utils import load_env

# Load environment variables
load_env()

# Fetch required environment variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ Telegram bot token is missing from environment variables.")

# Initialize the bot application
application = ApplicationBuilder().token(TOKEN).build()

# Enable logging
logging.basicConfig(level=logging.INFO)

def start_bot():
    """Start the bot and set the webhook."""
    logging.info("Starting the Homework Forwarder Bot...")
    from web import set_webhook
    set_webhook()
