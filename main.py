import os
import logging
import hashlib
import asyncio
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# Load environment variables
load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
SOURCE_CHAT_ID = os.getenv("SOURCE_CHAT_ID")
TARGET_CHAT_ID = os.getenv("TARGET_CHAT_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if not all([TOKEN, ADMIN_CHAT_ID, SOURCE_CHAT_ID, TARGET_CHAT_ID, WEBHOOK_URL]):
    raise ValueError("Missing required environment variables. Please check .env or Render settings.")

# Generate secure webhook path
SECRET_PATH = hashlib.sha256(TOKEN.encode()).hexdigest()

# Initialize logging
logging.basicConfig(level=logging.INFO)

# Initialize Flask and Telegram bot
app = Flask(__name__)
application = ApplicationBuilder().token(TOKEN).build()

# Health check for Render
@app.route('/')
def health():
    return "Bot is running", 200

# Webhook endpoint
@app.route(f'/{SECRET_PATH}', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    asyncio.run(application.process_update(update))
    return jsonify({"status": "ok"})

# Spam filter
def is_spam(text):
    spam_keywords = [
        "free", "click here", "buy now", "vpn", "offer", "subscribe", "promotion", "deal", "trial"
    ]
    return any(word in text.lower() for word in spam_keywords)

# Command: /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hi! I'm alive and ready to forward homework!")

# Main message handler
async def handle_homework(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    # Only accept from student group
    if update.effective_chat.id != int(SOURCE_CHAT_ID):
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text="❌ Rejected message. Not from source group.")
        return

    # Spam filtering
    if message.text and is_spam(message.text):
        await message.delete()
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"🚫 Spam removed: {message.text[:50]}")
        return

    # Forwarding logic
    if message.text or message.document or message.photo or message.video or message.voice:
        await context.bot.forward_message(
            chat_id=TARGET_CHAT_ID,
            from_chat_id=SOURCE_CHAT_ID,
            message_id=message.message_id
        )
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text="✅ Homework forwarded.")
    else:
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text="⚠️ Received but not forwarded. Not homework?")

# Register handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.ALL, handle_homework))

# Set webhook
async def set_webhook():
    await application.bot.set_webhook(url=f"{WEBHOOK_URL}/{SECRET_PATH}")
    logging.info("Webhook has been set.")

# Run the Flask app
if __name__ == "__main__":
    asyncio.run(set_webhook())
    from waitress import serve
    serve(app, host="0.0.0.0", port=8080)