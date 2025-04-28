import os
import re
import logging
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from telegram.error import TelegramError

# --- Flask App ---
app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Bot is live and healthy!", 200

# --- Environment Variables ---
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
TARGET_CHAT_ID = os.getenv("TARGET_CHAT_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if not TOKEN or not WEBHOOK_URL:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN or WEBHOOK_URL missing!")

# --- Logger ---
logging.basicConfig(level=logging.INFO)

# --- Telegram Application ---
application = ApplicationBuilder().token(TOKEN).build()

# --- Spam Detector ---
def is_spam(text: str) -> bool:
    spam_keywords = [
        "free", "click here", "buy now", "limited time", "offer", "deal",
        "visit", "subscribe", "discount", "special offer", "promotion",
        "win big", "urgent", "vpn", "start free trial", "get free access",
    ]
    url_pattern = r"https?://(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,6}(/[\w#!:.,?+=&%@!-/]*)?"

    return bool(
        re.search(url_pattern, text)
        or any(word in text.lower() for word in spam_keywords)
    )

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Bot is online and ready to forward homework!")

async def handle_homework(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    if not message:
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text="⚠️ Error: Received an invalid or empty message."
        )
        return

    try:
        # Spam Check
        if message.text and is_spam(message.text):
            await message.delete()
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"🚨 Spam deleted: {message.text[:50]}..."
            )
            return

        # Homework Detection
        if (
            (message.text and "homework" in message.text.lower())
            or message.document
            or message.photo
            or message.video
        ):
            await context.bot.forward_message(
                chat_id=TARGET_CHAT_ID,
                from_chat_id=update.effective_chat.id,
                message_id=message.message_id
            )
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"✅ Homework forwarded successfully."
            )
        else:
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text="⚠️ Message ignored: Not identified as homework."
            )

    except TelegramError as e:
        logging.error(f"Telegram Error: {e}")
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"❌ Telegram error: {e}"
        )
    except Exception as e:
        logging.error(f"General Error: {e}")
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"❌ General error: {e}"
        )

# --- Webhook Endpoint ---
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put_nowait(update)
    return jsonify({"status": "ok"}), 200

# Start the bot with webhook
if __name__ == "__main__":
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(set_webhook())  # Set the webhook
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))  # Start Flask server properly


# --- Register Handlers ---
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.ALL, handle_homework))

# --- Run Flask Server ---
if __name__ == "__main__":
