import os
import time
import logging
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from waitress import serve
from flask import Flask, request

from telegram import Bot, Update
from telegram.ext import (
    Application,
    MessageHandler,
    filters,
    ContextTypes
)

# Load environment variables
load_dotenv()

TOKEN = os.getenv("TOKEN")
SOURCE_CHAT_ID = int(os.getenv("SOURCE_CHAT_ID"))
TARGET_CHAT_ID = int(os.getenv("TARGET_CHAT_ID"))
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))

# Keywords for detecting homework
KEYWORDS = ["homework", "assignment", "worksheet"]

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot & App Setup
bot = Bot(token=TOKEN)
telegram_app = Application.builder().token(TOKEN).build()

# Track uptime
start_time = time.time()

# Flask app for webhook + health
app = Flask(__name__)

@app.route("/health", methods=["GET"])
def health():
    uptime = time.time() - start_time
    return {
        "status": "ok",
        "uptime_seconds": uptime,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), bot)
        telegram_app.update_queue.put_nowait(update)
        return "OK", 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return "Error", 500

# Forwarding Logic
async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or message.chat.id != SOURCE_CHAT_ID:
        return

    text_content = message.text or message.caption or ""
    text_lower = text_content.lower()

    if any(keyword in text_lower for keyword in KEYWORDS):
        try:
            if message.text:
                await bot.send_message(chat_id=TARGET_CHAT_ID, text=message.text)
            elif message.photo:
                await bot.send_photo(chat_id=TARGET_CHAT_ID, photo=message.photo[-1].file_id, caption=message.caption or "")
            elif message.document:
                await bot.send_document(chat_id=TARGET_CHAT_ID, document=message.document.file_id, caption=message.caption or "")

            logger.info(f"✅ Forwarded: {text_content[:30]}...")
            await bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"✅ Forwarded homework: {text_content[:30]}...")

        except Exception as e:
            logger.error(f"❌ Forwarding failed: {e}")
            await bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"⚠️ Error forwarding: {e}")
    else:
        logger.info(f"ℹ️ Skipped non-homework: {text_content[:30]}...")

telegram_app.add_handler(MessageHandler(filters.ALL, forward_message))

# Webhook startup
async def startup():
    webhook_url = "https://homework-bot-wxi3.onrender.com/webhook"  # Your actual Render URL
    await bot.set_webhook(url=webhook_url)
    logger.info("🚀 Webhook set successfully.")
    await bot.send_message(chat_id=ADMIN_CHAT_ID, text="✅ Homework Bot is running!")

# Main
if __name__ == "__main__":
    try:
        asyncio.run(startup())
    except RuntimeError as e:
        logger.error(f"Startup error: {e}")

    logger.info("🌐 Serving Flask via Waitress...")
    serve(app, host="0.0.0.0", port=8080)
