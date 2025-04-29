import logging
import os
import re
import hashlib
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes
from telegram.ext import filters
from telegram.error import TelegramError
from waitress import serve

# Load environment variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
TARGET_CHAT_ID = os.getenv("TARGET_CHAT_ID")
SOURCE_CHAT_ID = os.getenv("SOURCE_CHAT_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if not TOKEN or not WEBHOOK_URL or not SOURCE_CHAT_ID:
    raise ValueError("Required environment variables are missing: TOKEN, WEBHOOK_URL, or SOURCE_CHAT_ID.")

# Generate secure webhook path
SECRET_PATH = hashlib.sha256(TOKEN.encode()).hexdigest()

# Initialize Flask and Telegram app
app = Flask(__name__)
application = ApplicationBuilder().token(TOKEN).build()

# Enable logging
logging.basicConfig(level=logging.INFO)

# 🔒 Anti-spam filter
def is_spam(text):
    SPAM_KEYWORDS = [
        "free", "click here", "buy now", "limited time", "offer", "deal", "visit", "subscribe",
        "discount", "special offer", "promotion", "win big", "urgent", "click to claim", "winning",
        "vpn", "start free trial", "get free access", "limited offer"
    ]
    if re.search(r"https?://(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,6}(:\d+)?(/[\w#!:.,?+=&%@!-/]*)?", text):
        return True
    if any(word in text.lower() for word in SPAM_KEYWORDS):
        return True
    return False

# ✅ Message handler
async def handle_homework(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = update.message
        logging.info(f"📩 Incoming message: {message.text}")

        if update.effective_chat.id != int(SOURCE_CHAT_ID):
            await message.delete()
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text="⚠️ Message rejected. Not from a trusted group.")
            return

        if not message:
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text="⚠️ Empty message received.")
            return

        if message.text and is_spam(message.text):
            await message.delete()
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"🚨 Spam deleted: {message.text[:100]}")
            return

        if message.text and "homework" in message.text.lower() or message.document or message.photo or message.video:
            await context.bot.forward_message(chat_id=TARGET_CHAT_ID, from_chat_id=update.effective_chat.id, message_id=message.message_id)
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"✅ Homework forwarded from {update.effective_chat.title or update.effective_chat.id}")
        else:
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text="⚠️ No valid homework found.")

    except TelegramError as e:
        logging.error(f"Telegram error: {e}")
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"⚠️ Telegram error: {e}")
    except Exception as e:
        logging.error(f"General error: {e}")
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"⚠️ Error: {e}")

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Bot is online and ready to forward homework!")

# Register handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.ALL, handle_homework))

# ✅ One single webhook route using secure path
@app.route(f'/{SECRET_PATH}', methods=['POST'])
def webhook():
    update = request.get_json()
    update_obj = Update.de_json(update, application.bot)
    application.process_update(update_obj)
    return jsonify({"status": "ok"}), 200

# Webhook setup function
async def set_webhook():
    bot = application.bot
    secure_url = f"{WEBHOOK_URL}/{SECRET_PATH}"
    await bot.set_webhook(url=secure_url)

# Start server
if __name__ == "__main__":
    serve(app, host="0.0.0.0", port=8080)
