import logging
import os
import re
import asyncio
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from telegram.error import TelegramError

# Initialize Flask app
app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO)

# Get environment variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
TARGET_CHAT_ID = os.getenv("TARGET_CHAT_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Example: https://your-app-name.onrender.com

if not TOKEN or not WEBHOOK_URL:
    raise ValueError("Missing TELEGRAM_BOT_TOKEN or WEBHOOK_URL!")

# Initialize the bot
application = ApplicationBuilder().token(TOKEN).build()

# Detect spam function
def is_spam(text):
    SPAM_KEYWORDS = [
        "free", "click here", "buy now", "limited time", "offer", "deal", "visit", "subscribe",
        "discount", "special offer", "promotion", "win big", "urgent", "click to claim", "winning",
        "vpn", "start free trial", "get free access", "limited offer"
    ]
    if re.search(r"https?://", text):
        return True
    if any(word in text.lower() for word in SPAM_KEYWORDS):
        return True
    return False

# Handler for homework
async def handle_homework(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = update.message

        if not message:
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text="⚠️ Empty message received.")
            return

        if message.text and is_spam(message.text):
            await message.delete()
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"🚨 Spam deleted: {message.text[:100]}")
            return

        if message.text and "homework" in message.text.lower() or message.document or message.photo or message.video:
            await context.bot.forward_message(chat_id=TARGET_CHAT_ID, from_chat_id=update.effective_chat.id, message_id=message.message_id)
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"✅ Homework forwarded.")
        else:
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text="⚠️ Invalid message, not forwarded.")

    except TelegramError as e:
        logging.error(f"Telegram Error: {e}")
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"⚠️ Telegram Error: {e}")
    except Exception as e:
        logging.error(f"General Error: {e}")
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"⚠️ General Error: {e}")

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Bot is online and ready to forward homework!")

# Register handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.ALL, handle_homework))

# Flask route for webhook
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()
    update_obj = Update.de_json(update, application.bot)
    asyncio.run(application.process_update(update_obj))
    return jsonify({"status": "ok"}), 200

# Set webhook function
async def set_webhook():
    webhook_url = f"{WEBHOOK_URL}/{TOKEN}"
    await application.bot.set_webhook(url=webhook_url)
    logging.info(f"Webhook set to {webhook_url}")

# Main entry
if __name__ == "__main__":
    asyncio.run(set_webhook())
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
