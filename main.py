import os
import re
import logging
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes
from telegram.ext import filters
from telegram.error import TelegramError
from dotenv import load_dotenv
import hashlib
from waitress import serve

# Load environment variables from .env file
load_dotenv()

# Fetch all necessary variables from .env
TOKEN = os.getenv("TOKEN")
SOURCE_CHAT_ID = int(os.getenv("SOURCE_CHAT_ID"))
TARGET_CHAT_ID = int(os.getenv("TARGET_CHAT_ID"))
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Validate token and webhook URL
if not TOKEN or not WEBHOOK_URL or not SOURCE_CHAT_ID:
    raise ValueError("❌ One or more required environment variables are missing. Please check your .env file.")

# Set up logging
logging.basicConfig(level=logging.INFO)

# Generate secure webhook path
SECRET_PATH = hashlib.sha256(TOKEN.encode()).hexdigest()

# Initialize Flask and Telegram app
app = Flask(__name__)
application = ApplicationBuilder().token(TOKEN).build()

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

# ✅ Message handler to forward homework
async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    if not message:  # If message is empty or invalid, just return
        return

    text_content = message.text or message.caption or ""

    # Check if the message is from the source group
    if message.chat.id != SOURCE_CHAT_ID:
        await message.delete()
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text="⚠️ Message rejected. Not from a trusted group.")
        return

    # Spam check
    if is_spam(text_content):
        await message.delete()
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"🚨 Spam detected and deleted: {text_content[:40]}...")
        return

    # Check for homework-related content
    if "homework" in text_content.lower() or message.document or message.photo or message.video:
        try:
            # Forward message to the parent group
            if message.text:
                await context.bot.send_message(chat_id=TARGET_CHAT_ID, text=message.text)
            elif message.photo:
                await context.bot.send_photo(chat_id=TARGET_CHAT_ID, photo=message.photo[-1].file_id, caption=message.caption or "")
            elif message.document:
                await context.bot.send_document(chat_id=TARGET_CHAT_ID, document=message.document.file_id, caption=message.caption or "")

            # Admin notification
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"✅ Homework forwarded:\n🔹 From: {message.chat.title or message.chat.id}\n🔹 Content: {text_content[:100]}..."
            )

        except TelegramError as e:
            logging.error(f"Telegram error: {e}")
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"⚠️ Error forwarding homework: {e}")

    else:
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text="⚠️ No valid homework found.")

# Start command for bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Bot is online and ready to forward homework!")

# Register handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.ALL, forward_message))

# ✅ Webhook route
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

# Start Flask server and set webhook
if __name__ == "__main__":
    logging.info("🚀 Bot is running safely in Launch Mode")
    serve(app, host="0.0.0.0", port=8080)
    # Uncomment to enable webhook
    # asyncio.run(set_webhook())
