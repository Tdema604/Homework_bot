import logging
import os
import re
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes
from telegram.ext import filters  # Corrected import for filters
from telegram.error import TelegramError
from waitress import serve  # ✅ This was missing earlier

# Initialize Flask app
app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Bot is live and healthy!", 200

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
TARGET_CHAT_ID = os.getenv("TARGET_CHAT_ID")
SOURCE_CHAT_ID = os.getenv("SOURCE_CHAT_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if not TOKEN or not WEBHOOK_URL or not SOURCE_CHAT_ID:
    raise ValueError("Required environment variables are missing: TOKEN, WEBHOOK_URL, or SOURCE_CHAT_ID.")

application = ApplicationBuilder().token(TOKEN).build()

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

async def handle_homework(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = update.message

        if update.effective_chat.id != int(SOURCE_CHAT_ID):
            await message.delete()
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text="⚠️ Message rejected. Not from a trusted group.")
            return

        if not message:
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text="⚠️ Error: Received an invalid or empty message.")
            return

        if message.text and is_spam(message.text):
            await message.delete()
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"🚨 Spam message deleted: {message.text[:100]}")
            return

        if message.text and "homework" in message.text.lower() or message.document or message.photo or message.video:
            await context.bot.forward_message(chat_id=TARGET_CHAT_ID, from_chat_id=update.effective_chat.id, message_id=message.message_id)
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"✅ Homework forwarded from {update.effective_chat.title or update.effective_chat.id}.")
        else:
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text="⚠️ Invalid message type received. Please send a homework message.")

    except TelegramError as e:
        logging.error(f"Telegram Error: {e}")
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"⚠️ Error occurred while processing a message: {e}")
    except Exception as e:
        logging.error(f"General Error: {e}")
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"⚠️ General error: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot is online and ready to forward homework!")

application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.ALL, handle_homework))

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    update = request.get_json()
    update_obj = Update.de_json(update, application.bot)
    application.process_update(update_obj)
    return jsonify({"status": "ok"}), 200

async def set_webhook():
    bot = application.bot
    webhook_url = f"{WEBHOOK_URL}/{TOKEN}"
    await bot.set_webhook(url=webhook_url)

# ✅ This part below caused the "serve not defined" error earlier
if __name__ == "__main__":
    serve(app, host="0.0.0.0", port=8080)
