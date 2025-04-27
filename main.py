import logging
import os
import re
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError

# Initialize logging
logging.basicConfig(level=logging.INFO)

# Load environment variables securely
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
TARGET_CHAT_ID = os.getenv("TARGET_CHAT_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Make sure to set this in Render's environment variables

# Safety check
if not TOKEN or not WEBHOOK_URL:
    raise ValueError("TELEGRAM_BOT_TOKEN or WEBHOOK_URL missing in environment variables!")

# Create bot application instance
app = ApplicationBuilder().token(TOKEN).build()

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

# Example handler for forwarding homework messages
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
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.ALL, handle_homework))

async def set_webhook():
    bot = Bot(TOKEN)
    webhook_url = f"{WEBHOOK_URL}/{TOKEN}"  # Ensure correct URL format
    print(f"Webhook URL being set: {webhook_url}")  # Log for debugging
    await bot.set_webhook(url=webhook_url)


# Start bot with webhook
if __name__ == "__main__":
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(set_webhook())
    app.run_webhook(listen="0.0.0.0", port=int(os.getenv("PORT", 8080)), url_path=TOKEN)
