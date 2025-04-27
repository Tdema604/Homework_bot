import logging
from telegram import Update, InputMediaPhoto, InputMediaVideo, Document
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import re

# Set up logging to get feedback for troubleshooting
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Define your bot's variables
TOKEN = "your-telegram-bot-token"
SOURCE_GROUP_ID = "your-student-group-id"
TARGET_CHAT_ID = "your-parent-group-id"
ADMIN_CHAT_ID = "your-admin-user-id"  # Admin user ID for notifications

# Define the command handler for the /start command
async def start(update: Update, context):
    await update.message.reply_text('Bot is up and running!')

# Define the homework handler to filter and forward homework-related messages
async def homework_handler(update: Update, context):
    message = update.message.text.lower()
    if "homework" in message or "assignment" in message or "worksheet" in message:
        # Forward homework-related text messages to the parent group
        await context.bot.forward_message(chat_id=TARGET_CHAT_ID, from_chat_id=update.message.chat_id, message_id=update.message.message_id)
        # Notify the admin about the successful forwarding
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"Homework forwarded to the parent group: {update.message.text[:50]}...")

# Handle the different types of files (image, video, document, etc.)
async def homework_files_handler(update: Update, context):
    if update.message.photo:
        # Forward image files
        file = update.message.photo[-1].file_id  # Get the highest resolution image
        await context.bot.send_photo(chat_id=TARGET_CHAT_ID, photo=file, caption="Homework Image")
        # Notify the admin about the successful forwarding
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text="Homework Image forwarded to the parent group.")
    elif update.message.video:
        # Forward video files
        file = update.message.video.file_id
        await context.bot.send_video(chat_id=TARGET_CHAT_ID, video=file, caption="Homework Video")
        # Notify the admin about the successful forwarding
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text="Homework Video forwarded to the parent group.")
    elif update.message.document:
        # Forward document files (PDF, Word, etc.)
        file = update.message.document.file_id
        await context.bot.send_document(chat_id=TARGET_CHAT_ID, document=file, caption="Homework Document")
        # Notify the admin about the successful forwarding
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text="Homework Document forwarded to the parent group.")
    elif update.message.audio:
        # Forward audio files (if applicable)
        file = update.message.audio.file_id
        await context.bot.send_audio(chat_id=TARGET_CHAT_ID, audio=file, caption="Homework Audio")
        # Notify the admin about the successful forwarding
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text="Homework Audio forwarded to the parent group.")

# Define a spam filter to delete irrelevant messages
async def spam_filter(update: Update, context):
    message = update.message.text.lower()
    # Customize spam detection (add more patterns or keywords as needed)
    spam_keywords = ['free', 'win', 'offer', 'urgent', 'limited time', 'call now', 'click here', 'discount', 'sale', 'congratulations']
    
    # Check if the message contains any spam keyword
    if any(re.search(keyword, message) for keyword in spam_keywords):
        # Delete the message if it contains spam
        await update.message.delete()
        # Notify the admin about the deletion
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"Spam message deleted: {message[:50]}...")

# Main function to set up the bot
async def main():
    # Initialize the application and bot with your token
    application = Application.builder().token(TOKEN).build()

    # Set up the handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, homework_handler))
    application.add_handler(MessageHandler(filters.PHOTO, homework_files_handler))  # Handle images
    application.add_handler(MessageHandler(filters.VIDEO, homework_files_handler))  # Handle videos
    application.add_handler(MessageHandler(filters.DOCUMENT, homework_files_handler))  # Handle documents
    application.add_handler(MessageHandler(filters.AUDIO, homework_files_handler))  # Handle audio files
    application.add_handler(MessageHandler(filters.TEXT & filters.COMMAND, spam_filter))

    # Run the bot (this will start polling in the existing event loop)
    await application.run_polling()

# Ensure the event loop is properly managed, as Render might already be running an event loop
if __name__ == '__main__':
    import asyncio

    # If the event loop is already running (common in cloud environments like Render), just start the bot
    try:
        asyncio.get_event_loop().run_until_complete(main())
    except RuntimeError as e:
        if 'This event loop is already running' in str(e):
            # If the event loop is already running, we'll use asyncio.ensure_future to avoid the error
            asyncio.ensure_future(main())
        else:
            raise
