import os
import logging
import hashlib
import asyncio
import time
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError

# Load .env variables
load_dotenv()

# Fetch required environment variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
TARGET_CHAT_ID = os.getenv("TARGET_CHAT_ID")
SOURCE_CHAT_ID = os.getenv("SOURCE_CHAT_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if not TOKEN or not WEBHOOK_URL or not SOURCE_CHAT_ID:
    raise ValueError("❌ One or more required environment variables are missing. Check your .env file.")

# Generate secure webhook path
SECRET_PATH = hashlib.sha256(TOKEN.encode()).hexdigest()

# Initialize Flask and Telegram Application
app = Flask(__name__)
application = ApplicationBuilder().token(TOKEN).build()

# Enable logging
logging.basicConfig(level=logging.INFO)

# Anti-spam filter
def is_spam(text):
    SPAM_KEYWORDS = [
        "free", "click here", "buy now", "limited time", "offer", "deal", "visit", "subscribe",
        "discount", "promotion", "win big", "urgent", "vpn", "trial", "access", "claim", "winning"
    ]
    return any(word in text.lower() for word in SPAM_KEYWORDS)

# Message handler
async def handle_homework(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text="⚠️ Empty message received.")
        return

    if update.effective_chat.id != int(SOURCE_CHAT_ID):
        await message.delete()
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text="⚠️ Message rejected. Not from a trusted group.")
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

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Bot is online and ready to forward homework!")

# Notify admin when bot deploys
from datetime import datetime
from pytz import timezone

async def notify_admin_startup():
    try:
        bt_time = datetime.now(timezone("Asia/Thimphu")).strftime("%Y-%m-%d %I:%M:%S %p (BTT)")
        status_url = f"https://{WEBHOOK_URL.replace('https://', '').split('/')[0]}"
        await application.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"✅ Homework Bot deployed and active on Render!\n🕒 {bt_time}\n🌐 [Check Uptime]({status_url})",
            parse_mode="Markdown"
        )
    except Exception as e:
        logging.error(f"Failed to notify admin on startup: {e}")


# Register handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("status", status))
application.add_handler(MessageHandler(filters.ALL, handle_homework))

# Flask route to handle webhook
@app.route(f'/{SECRET_PATH}', methods=['POST'])
def webhook():
    update = request.get_json()
    update_obj = Update.de_json(update, application.bot)
    application.process_update(update_obj)
    return jsonify({"status": "ok"}), 200
@app.route("/", methods=["GET"])
def index():
    return "✅ Homework Bot is running!"
# Set webhook on startup
async def set_webhook():
    bot = application.bot
    secure_url = f"{WEBHOOK_URL}/{SECRET_PATH}"
    await bot.set_webhook(url=secure_url)
    logging.info(f"Webhook set to: {secure_url}")

# Start everything
async def setup():
    await set_webhook()
    await notify_admin_startup()

if __name__ == "__main__":
    asyncio.run(setup())

    from waitress import serve
    serve(app, host="0.0.0.0", port=8080)
    start_time = time.time()

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uptime_seconds = int(time.time() - start_time)
    hours, remainder = divmod(uptime_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime = f"{hours}h {minutes}m {seconds}s"

    await update.message.reply_text(f"✅ Bot is online.\n⏱ Uptime: {uptime}")


