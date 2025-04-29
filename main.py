import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from flask import Flask, request, jsonify
from telegram.error import TelegramError
import hashlib
import asyncio

# Load environment variables
load_dotenv()

# Fetch necessary environment variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
TARGET_CHAT_ID = os.getenv("TARGET_CHAT_ID")
SOURCE_CHAT_ID = os.getenv("SOURCE_CHAT_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Check if essential environment variables are loaded
if not TOKEN or not WEBHOOK_URL or not SOURCE_CHAT_ID:
    raise ValueError("❌ One or more required environment variables are missing. Please check your .env file.")

# Generate secure webhook path
SECRET_PATH = hashlib.sha256(TOKEN.encode()).hexdigest()

# Initialize Flask and Telegram bot application
app = Flask(__name__)
application = ApplicationBuilder().token(TOKEN).build()

# Enable logging
logging.basicConfig(level=logging.INFO)

# Anti-spam filter function
def is_spam(text):
    SPAM_KEYWORDS = [
        "free", "click here", "buy now", "limited time", "offer", "deal", "visit", "subscribe",
        "discount", "special offer", "promotion", "win big", "urgent", "click to claim", "winning",
        "vpn", "start free trial", "get free access", "limited offer"
    ]
    if any(word in text.lower() for word in SPAM_KEYWORDS):
        return True
    return False

# Define message handler function
async def handle_homework(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
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

# Start command function
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Bot is online and ready to forward homework!")

# Register handlers for commands and messages
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.ALL, handle_homework))

# Flask route for the webhook endpoint
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
    logging.info(f"Webhook set to: {secure_url}")

# Main entry point
if __name__ == "__main__":
    # Set the webhook (run once before starting the Flask server)
    asyncio.run(set_webhook())

    # Start the Flask server
    from waitress import serve
    serve(app, host="0.0.0.0", port=8080)  # You can change the port if needed
