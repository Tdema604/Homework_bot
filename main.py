import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import logging

# Load the environment variables
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID')
TARGET_CHAT_ID = os.getenv('TARGET_CHAT_ID')

# Set up logging
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger()

async def forward_homework(update: Update, context):
    if 'homework' in update.message.text.lower():
        try:
            # Forward the message to the parent group
            if update.message.text:
                await context.bot.send_message(chat_id=TARGET_CHAT_ID, text=update.message.text)
            if update.message.photo:
                await context.bot.send_photo(chat_id=TARGET_CHAT_ID, photo=update.message.photo[-1].file_id)
            if update.message.document:
                await context.bot.send_document(chat_id=TARGET_CHAT_ID, document=update.message.document.file_id)
            
            # Notify admin
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"Homework forwarded: {update.message.text[:50]}...")
            logger.info("Message forwarded successfully.")
        except Exception as e:
            logger.error(f"Error forwarding message: {e}")
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"Error forwarding message: {str(e)}")
    else:
        logger.info("No homework keyword detected.")

# Set up the bot application
async def main():
    application = Application.builder().token(TOKEN).build()
    
    start_handler = CommandHandler("start", lambda update, context: update.message.reply_text("Bot is running"))
    application.add_handler(start_handler)

    message_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, forward_homework)
    application.add_handler(message_handler)
    
    # Run the bot
    await application.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
