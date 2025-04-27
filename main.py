import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Define the bot token and other variables
TOKEN = "your-telegram-bot-token"
SOURCE_GROUP_ID = "your-student-group-id"
TARGET_CHAT_ID = "your-parent-group-id"
ADMIN_CHAT_ID = "your-admin-user-id"

# Define command handler to start bot
async def start(update: Update, context):
    await update.message.reply_text('Bot is up and running!')

# Define message handler for homework-related messages
async def homework_handler(update: Update, context):
    message = update.message.text.lower()
    if "homework" in message or "assignment" in message or "worksheet" in message:
        # Forward the message to the parent group
        await context.bot.forward_message(chat_id=TARGET_CHAT_ID, from_chat_id=update.message.chat_id, message_id=update.message.message_id)

# Define message handler for spam filtering
async def spam_filter(update: Update, context):
    message = update.message.text.lower()
    if "spam" in message:  # Customize the spam filter logic
        await update.message.delete()

# Main function to set up the bot
async def main():
    # Initialize the bot and application
    application = Application.builder().token(TOKEN).build()

    # Set up handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, homework_handler))
    application.add_handler(MessageHandler(filters.TEXT & filters.COMMAND, spam_filter))

    # Start the bot
    await application.run_polling()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
