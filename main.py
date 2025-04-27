import logging
import os
import re
from flask import Flask, request, jsonify
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError

# Initialize logging
logging.basicConfig(level=logging.INFO)

# Load environment variables securely
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
TARGET_CHAT_ID = os.getenv("TARGET_CHAT_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Safety check
if not TOKEN or not WEBHOOK_URL:
    raise ValueError("TELEGRAM_BOT_TOKEN or WEBHOOK_URL missing in environment variables!")

# Initialize Flask app
app = Flask(__name__)

# Create bot application instance
bot = Bot(TOKEN)
application = ApplicationBuilder().token(TOKEN).build()

# List of suspicious words/phrases that often appear in spam
SPAM_KEYWORDS = [
    "free", "click here", "buy now", "limited time", "offer", "deal", "visit", "subscribe",
    "discount", "special offer", "promotion", "win big", "click to claim", "winning"
]

# Function to detect spam based on suspicious patterns in text
def is_spam(text):
    # Check for suspicious words/phrases
    if any(word in text.lower() for word in SPAM_KEYWORDS):
        return True

    # Check for links (basic link pattern)
    if re.search(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+", text):
        return True
    
    return False

# Function to handle homework forwarding
async def handle_homework(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = update.message

        # Check if message exists and isn't None
        if not message:
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"⚠️ Error: Received an invalid or empty message in group: {update.effective_chat.title or update.effective_chat.id}"
            )
            return

        # Check if message is spam
        if message.text and is_spam(message.text):
            await message.delete()
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"🚨 Spam message deleted from {update.effective_chat.title or update.effective_chat.id}. Message: {message.text[:100]}"
            )
            return

        # Acceptable file types for homework (Text, Image, Doc, Video)
        if (message.text and "homework" in message.text.lower()) or \
           message.document or message.photo or message.video:

            # Forward the message
            await context.bot.forward_message(
                chat_id=TARGET_CHAT_ID,
                from_chat_id=update.effective_chat.id,
                message_id=message.message_id
            )

            # Notify Admin
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"✅ Homework forwarded from group: {update.effective_chat.title or update.effective_chat.id}"
            )

        else:
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"⚠️ Invalid message type received: {update.effective_chat.title or update.effective_chat.id}. Message: {message.text[:100]}"
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

# Optional command: /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot is online and ready to forward homework!")

# Register Handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.ALL, handle_homework))

# Set webhook route for Flask
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    update = request.get_json()  # Get the incoming update from Telegram
    application.process_new_updates([Update.de_json(update, bot)])  # Process the update with python-telegram-bot
    return jsonify({"status": "ok"}), 200

# Set Webhook
def set_webhook():
    url = f"https://homework-bot-wxi3.onrender.com/{TOKEN}"
    response = bot.set_webhook(url)
    if response:
        logging.info(f"Webhook set successfully at {url}")
    else:
        logging.error("Failed to set webhook.")

if __name__ == "__main__":
    set_webhook()  # Set the webhook
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))  # Start Flask app
