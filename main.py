import os
import telegram
from telegram.ext import Application, MessageHandler, filters
from dotenv import load_dotenv
from flask import Flask
import threading

# Load environment variables
load_dotenv()

# Fetch environment variables
TOKEN = os.getenv("TOKEN")
SOURCE_GROUP_ID = int(os.getenv("SOURCE_GROUP_ID"))
TARGET_CHAT_ID = int(os.getenv("TARGET_CHAT_ID"))
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))

# Initialize bot
bot = telegram.Bot(token=TOKEN)

# Keywords for forwarding
keywords = ["homework", "assignment", "worksheet"]

# Start Flask app for Render health check
app_flask = Flask('')

@app_flask.route('/')
def home():
    return "Bot is running!"

def run_flask():
    port = int(os.environ.get('PORT', 5000))
    app_flask.run(host="0.0.0.0", port=port)

# Message forwarding logic
async def forward_message(update, context):
    message = update.message

    if message.chat.id == SOURCE_GROUP_ID:
        if message.text and any(keyword.lower() in message.text.lower() for keyword in keywords):
            await bot.send_message(chat_id=TARGET_CHAT_ID, text=message.text)
        elif message.photo:
            if message.caption and any(keyword.lower() in message.caption.lower() for keyword in keywords):
                await bot.send_photo(chat_id=TARGET_CHAT_ID, photo=message.photo[-1].file_id, caption=message.caption)
        elif message.document:
            if message.caption and any(keyword.lower() in message.caption.lower() for keyword in keywords):
                await bot.send_document(chat_id=TARGET_CHAT_ID, document=message.document.file_id, caption=message.caption)
        else:
            print("⚡ Non-homework message detected, ignoring...")

# Start Telegram bot
def start_bot():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, forward_message))
    print("🚀 Bot is running and polling for messages...")
    app.run_polling()

if __name__ == '__main__':
    threading.Thread(target=run_flask).start()  # Start fake web server
    start_bot()  # Start the bot
