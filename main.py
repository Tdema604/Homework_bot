import logging
import os
import re
import time
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError

# Initialize Flask app
app = Flask(__name__)

# Logging setup
logging.basicConfig(level=logging.INFO)

# Environment variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
TARGET_CHAT_ID = os.getenv("TARGET_CHAT_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if not TOKEN or not WEBHOOK_URL:
    raise ValueError("Environment variables missing: TELEGRAM_BOT_TOKEN or WEBHOOK_URL.")

# Initialize bot
application = ApplicationBuilder().token(TOKEN).build()

# Rate limiting (simple)
user_last_message_time = {}

# Spam detection function
def is_spam(text):
    SPAM_KEYWORDS = [
        "free", "click here", "buy now", "limited time", "offer", "deal", "visit", "subscribe",
        "discount", "special offer", "promotion", "win big", "urgent", "click to claim", "winning",
        "vpn", "start free trial", "get free access", "limited offer"
    ]
    if re.search(r"https?://(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,6}(/[\w#!:.,?+=&%@!-/]*)?", text):
        return True
    if any(word in text.lower() for word in SPAM_KEYWORDS):
        return True
    return False

# Detect repeated emojis or text
def is_repeated_text(message):
    words = message.split()
    if len(set(words)) < len(words) / 2:
        return True
    return False

# Basic rate limiting
def is_spammer(user_id):
    current_time = time.time()
    if user_id in user_last_message_time:
        if (current_time - user_last_message_time[user_id]) < 5:
            return True
    user_last_message_time[user_id] = current_time
    return False

# Homework handler
async def handle_homework(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = update.message
        if not message:
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text="⚠️ Received an empty or invalid message.")
            return

        if message.text:
            if is_spam(message.text) or is_repeated_text(message.text) or is_spammer(message.from_user.id):
                await message.delete()
                await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"🚨 Spam detected and deleted: {message.text[:100]}")
                return

        if message.text and "homework" in message.text.lower() or message.document or message.photo or message.video:
            await context.bot.forward_message(chat_id=TARGET_CHAT_ID, from_chat_id=update.effective_chat.id, message_id=message.message_id)
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"✅ Homework forwarded from {update.effective_chat.title or update.effective_chat.id}.")
        else:
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text="⚠️ Received an unsupported message type.")

    except TelegramError as e:
        logging.error(f"Telegram Error: {e}")
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"⚠️ Telegram error: {e}")
    except Exception as e:
        logging.error(f"General Error: {e}")
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"⚠️ General error: {e}")

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot is live and ready to forward homework!")

# /ban command
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check if the user is admin
    if update.message.from_user.id != int(ADMIN_CHAT_ID):
        await update.message.reply_text("⚠️ You are not authorized to use this command.")
        return

    # Get the username to ban
    if len(context.args) != 1:
        await update.message.reply_text("⚠️ Please provide the username to ban, e.g., /ban @username")
        return
    
    username = context.args[0].lstrip('@')
    
    # Try to find the user by username
    user = None
    try:
        # Get the list of chat members
        members = await update.effective_chat.get_members()

        # Search for the user by username
        for member in members:
            if member.user.username == username:
                user = member
                break
    except Exception as e:
        await update.message.reply_text(f"⚠️ Failed to fetch chat members: {e}")

    if user:
        try:
            # Ban the user from the chat
            await context.bot.kick_chat_member(update.effective_chat.id, user.user.id)
            await update.message.reply_text(f"✅ {username} has been banned successfully.")
        except Exception as e:
            await update.message.reply_text(f"⚠️ Failed to ban {username}: {e}")
    else:
        await update.message.reply_text(f"⚠️ Could not find user @{username} in the chat.")

# Register the command handler without 'pass_args'
application.add_handler(CommandHandler("ban", ban))  # No need for 'pass_args'


# Flask Home route
@app.route("/")
def home():
    return "✅ Bot is live!", 200

# Webhook route
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    update = request.get_json()
    update_obj = Update.de_json(update, application.bot)
    application.process_update(update_obj)
    return jsonify({"status": "ok"}), 200

# Set webhook
async def set_webhook():
    bot = application.bot
    await bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")

# Register handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("ban", ban, pass_args=True))  # Passes arguments to /ban
application.add_handler(MessageHandler(filters.ALL, handle_homework))

# Start app
if __name__ == "__main__":
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(set_webhook())
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
