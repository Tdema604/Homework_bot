from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters
from telegram import Update
import os
import logging
from telegram.error import TelegramError
import re
from telegram.ext import ContextTypes

# Setup logging
logging.basicConfig(level=logging.INFO)

# Load environment variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))
TARGET_CHAT_ID = int(os.getenv("TARGET_CHAT_ID"))

# Safety checks
if not TOKEN or not ADMIN_CHAT_ID or not TARGET_CHAT_ID:
    raise ValueError("Missing critical environment variables!")

# Build the bot application
app = ApplicationBuilder().token(TOKEN).build()

# List of suspicious words/phrases that often appear in spam
SPAM_KEYWORDS = [
    "free", "click here", "buy now", "limited time", "offer", "deal", "visit", "subscribe",
    "discount", "special offer", "promotion", "win big", "urgent", "click to claim", "winning"
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

# Handler for homework messages (Text, Image, Doc, Video)
async def forward_homework(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = update.message

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
app.add_handler(MessageHandler(filters.ALL, forward_homework))

# Start polling
if __name__ == "__main__":
    app.run_polling()
