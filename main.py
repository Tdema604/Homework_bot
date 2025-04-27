import logging
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters, CallbackContext
import os

# Initialize Flask app
app = Flask(__name__)

# Logging setup for better traceability
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.FileHandler('bot.log'), logging.StreamHandler()])
logger = logging.getLogger(__name__)

# Your bot's token and other necessary configuration
TOKEN = os.getenv("TOKEN")
SOURCE_GROUP_ID = os.getenv("SOURCE_GROUP_ID")
TARGET_CHAT_ID = os.getenv("TARGET_CHAT_ID")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

# Initialize the Telegram Bot
bot = Bot(TOKEN)

def start(update: Update, context: CallbackContext):
    """Respond to /start command."""
    logger.info("Bot started.")
    update.message.reply_text("Hello, I'm your bot for homework forwarding!")

def forward_homework(update: Update, context: CallbackContext):
    """Forward homework messages to the parent group."""
    logger.info(f"Forwarding homework message from {update.message.from_user.username} to parent group.")
    context.bot.forward_message(chat_id=TARGET_CHAT_ID, from_chat_id=update.message.chat_id, message_id=update.message.message_id)

def forward_media(update: Update, context: CallbackContext):
    """Forward media (images, documents, PDFs, etc.) related to homework."""
    logger.info(f"Forwarding media message from {update.message.from_user.username} to parent group.")
    media = None
    if update.message.photo:
        # Forward the first photo
        media = update.message.photo[-1].file_id
    elif update.message.document:
        # Forward the document (could be PDF, Word, etc.)
        media = update.message.document.file_id

    if media:
        context.bot.send_document(chat_id=TARGET_CHAT_ID, document=media, caption=update.message.caption)

def filter_homework(update: Update, context: CallbackContext):
    """Filter homework-related messages based on keywords."""
    message_text = update.message.text.lower()
    homework_keywords = ["homework", "assignment", "worksheet", "pdf", "word document", "study material"]

    # Check if the message contains homework keywords
    if any(keyword in message_text for keyword in homework_keywords):
        # Forward text messages if they contain homework-related keywords
        forward_homework(update, context)
        
        # Check and forward any media (images, documents, PDFs, etc.)
        forward_media(update, context)
    else:
        # If it's not a homework message, delete the message
        update.message.delete()
        logger.info(f"Deleted non-homework message from {update.message.from_user.username}")

# Webhook route to handle incoming updates from Telegram
@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook handler for receiving updates from Telegram."""
    json_str = request.get_data().decode('UTF-8')
    update = Update.de_json(json_str, bot)
    dispatcher.process_update(update)
    return 'ok'

# Set webhook when bot is deployed
def set_webhook():
    """Set up the webhook with your Render URL."""
    webhook_url = os.getenv("WEBHOOK_URL")  # Ensure you configure this in Render's dashboard
    bot.set_webhook(url=webhook_url + "/webhook")
    logger.info(f"Webhook set to {webhook_url}/webhook")

def main():
    """Main entry point for the bot."""
    global dispatcher

    # Setup the dispatcher
    dispatcher = Dispatcher(bot, None)

    # Command Handlers
    dispatcher.add_handler(CommandHandler("start", start))

    # Filter homework-related messages and forward them
    dispatcher.add_handler(MessageHandler(Filters.text, filter_homework))
    dispatcher.add_handler(MessageHandler(Filters.photo | Filters.document, filter_homework))

    # Set up webhook after bot initialization
    set_webhook()

if __name__ == '__main__':
    main()

    # Run the Flask app with Gunicorn (for production)
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
