import os
import re
import logging
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError

# Initialize Flask app
app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO)

# Get environment variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
TARGET_CHAT_ID = os.getenv("TARGET_CHAT_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
SOURCE_CHAT_ID = os.getenv("SOURCE_CHAT_ID")  # 💥 Added trusted source group ID!

# Safety check
if not TOKEN or not WEBHOOK_URL or not SOURCE_CHAT_ID:
    raise ValueError("Required environment variables are missing: TOKEN, WEBHOOK_URL, or SOURCE_CHAT_ID.")

# Initialize the bot application
application = ApplicationBuilder().token(TOKEN).build()

# Define a simple home route
@app.route("/")
def home():
    return "✅ Bot is live and healthy!", 200

# Function to detect spam messages
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

# Homework handler
async def handle_homework(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = update.message

        # Validate source chat
        if str(update.effective_chat.id) != SOURCE_CHAT_ID:
            logging.warning(f"Unauthorized message from {update.effective_chat.id}")
            return

        if not message:
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text="⚠️ Error: Empty message received.")
            return

        # Check for spam
        if message.text and is_spam(message.text):
            await message.delete()
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"🚨 Spam message deleted: {message.text[:100]}"
            )
            return

        # Forward homework or educational materials
        if message.text and "homework" in message.text.lower() or message.document or message.photo or message.video:
            await context.bot.forward_message(
                chat_id=TARGET_CHAT_ID,
                from_chat_id=update.effective_chat.id,
                message_id=message.message_id
            )
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"✅ Homework forwarded from {update.effective_chat.title or update.effective_chat.id}."
            )
        else:
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text="⚠️ Received a non-homework message."
            )

    except TelegramError as e:
        logging.error(f"Telegram Error: {e}")
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"⚠️ Telegram error: {e}")
    except Exception as e:
        logging.error(f"General Error: {e}")
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"⚠️ General error: {e}")

# Optional /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot is active and ready to forward homework!")

# Register handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.ALL, handle_homework))

# Webhook route
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json(force=True)
    update_obj = Update.de_json(update, application.bot)
    application.update_queue.put_nowait(update_obj)
    return jsonify({"status": "ok"}), 200

# Set webhook on Telegram side
async def set_webhook():
    bot = application.bot
    webhook_url = f"{WEBHOOK_URL}/{TOKEN}"
    await bot.set_webhook(url=webhook_url)

# Run app
if __name__ == "__main__":
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(set_webhook())
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
