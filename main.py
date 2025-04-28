import logging
import os
import re
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, Filters, ContextTypes
from telegram.error import TelegramError
import time

# Initialize Flask app
app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO)

# Get environment variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
TARGET_CHAT_ID = os.getenv("TARGET_CHAT_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Safety check
if not TOKEN or not WEBHOOK_URL:
    raise ValueError("TELEGRAM_BOT_TOKEN or WEBHOOK_URL missing in environment variables!")

# Initialize the bot application
application = ApplicationBuilder().token(TOKEN).build()

# Global dictionary to store users' last message time (for rate limiting)
user_last_message_time = {}

# Function to detect spam in messages
def is_spam(text):
    SPAM_KEYWORDS = [
        "free", "click here", "buy now", "limited time", "offer", "deal", "visit", "subscribe",
        "discount", "special offer", "promotion", "win big", "urgent", "click to claim", "winning",
        "vpn", "start free trial", "get free access", "limited offer"
    ]
    # Detect URLs and common spam words
    if re.search(r"https?://(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,6}(:\d+)?(/[\w#!:.,?+=&%@!-/]*)?", text):
        return True
    if any(word in text.lower() for word in SPAM_KEYWORDS):
        return True
    return False

# Function to detect repeated messages (emojis or identical text)
def is_repeated_text(message):
    # Example of detecting too many emojis or repeated words in the message
    if len(set(message.split())) < len(message.split()) / 2:
        return True
    return False

# Rate limiting function to prevent message spam from users
def is_spammer(user_id):
    current_time = time.time()
    if user_id in user_last_message_time:
        time_diff = current_time - user_last_message_time[user_id]
        if time_diff < 5:  # Block users who send messages faster than 5 seconds
            return True
    user_last_message_time[user_id] = current_time
    return False

# Function to handle homework messages
async def handle_homework(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = update.message

        # Check if the message is not empty
        if not message:
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text="⚠️ Error: Received an invalid or empty message."
            )
            return

        # Check if the message is spam
        if message.text and is_spam(message.text):
            await message.delete()
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"🚨 Spam message deleted: {message.text[:100]}"
            )
            return

        # Check for repeated messages (e.g., emojis or duplicate content)
        if message.text and is_repeated_text(message.text):
            await message.delete()
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"🚨 Repeated/spam message deleted: {message.text[:100]}"
            )
            return

        # Check for rate limiting (messages sent too frequently)
        if is_spammer(update.message.from_user.id):
            await message.delete()
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"🚨 Spammer detected and message deleted: {message.text[:100]}"
            )
            return

        # If it's homework (message containing "homework" or a file), forward it
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
                text="⚠️ Invalid message type received. Please send a homework message."
            )

    except TelegramError as e:
        logging.error(f"Telegram Error: {e}")
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"⚠️ Error occurred while processing a message: {e}"
        )
    except Exception as e:
        logging.error(f"General Error: {e}")
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"⚠️ General error: {e}"
        )

# Optional /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot is online and ready to forward homework!")

# Register handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(Filters.ALL, handle_homework))

# Set Webhook route
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    update = request.get_json()  # Get the incoming update from Telegram
    update_obj = Update.de_json(update, application.bot)  # Convert JSON to Telegram Update object
    application.process_update(update_obj)  # Process the update with the application
    return jsonify({"status": "ok"}), 200

# Set webhook for the bot
async def set_webhook():
    bot = application.bot
    webhook_url = f"{WEBHOOK_URL}/{TOKEN}"
    await bot.set_webhook(url=webhook_url)

# Start the bot with webhook
if __name__ == "__main__":
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(set_webhook())  # Set the webhook
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))  # Start Flask server
