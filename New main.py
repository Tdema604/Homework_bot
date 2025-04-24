from flask import Flask
import telegram
from telegram.ext import Updater, MessageHandler, Filters
import os
from threading import Thread

# Replace these with your actual bot token and group IDs
BOT_TOKEN = "YOUR_BOT_TOKEN"
SOURCE_CHAT_ID = -4703962156 # Student group
TARGET_CHAT_ID = -1002287165008 # Parent group

# Initialize bot
bot = telegram.Bot(token=BOT_TOKEN)

# Function to forward homework messages
def forward_homework(update, context):
    message_text = update.message.text.lower()
    if any(keyword in message_text for keyword in ["homework", "worksheet", "assignment"]):
        context.bot.forward_message(chat_id=TARGET_CHAT_ID,
                                    from_chat_id=update.message.chat_id,
                                    message_id=update.message.message_id)

# Start the Telegram bot in a thread
def start_bot():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(MessageHandler(Filters.text & Filters.chat(chat_id=SOURCE_CHAT_ID), forward_homework))
    updater.start_polling()
    updater.idle()

# Healthcheck Flask app
app = Flask(__name__)

@app.route('/')
def home():
    return "I'm alive!"

if __name__ == '__main__':
    Thread(target=start_bot).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
