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
            await context.bot.send_message(chat_id=ADMIN
