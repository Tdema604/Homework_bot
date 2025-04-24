from flask import Flask
import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import os
from threading import Thread

# Replace these with your actual bot token and group IDs
BOT_TOKEN = 7780579160:AAE-DWc3B6GkgMgvueHomHOF65AmciT10ac
SOURCE_CHAT_ID = -4703962156 # Student group
TARGET_CHAT_ID = -1002287165008 # Parent group

# Initialize bot
TOKEN = os.environ.get(7780579160:AAE-DWc3B6GkgMgvueHomHOF65AmciT10ac)
bot = telegram.Bot(token=TOKEN)

# Function to forward homework messages
def forward_homework(update, context):
    message_text = update.message.text.lower()
    if any(keyword in message_text for keyword in ["homework", "worksheet", "assignment"]):
        context.bot.forward_message(chat_id=TARGET_CHAT_ID,
                                    from_chat_id=update.message.chat_id,
                                    message_id=update.message.message_id)
        
 # For webhook response (Render keeps service awake)
app = Flask(__name__)

# Start the Telegram bot in a thread
def start_bot():
   updater = Updater(7780579160:AAE-DWc3B6GkgMgvueHomHOF65AmciT10ac, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(MessageHandler(Filters.text & Filters.chat(chat_id=SOURCE_CHAT_ID), forward_homework))
    updater.start_polling()
    updater.idle()

# Define a simple start command
def start(update, context):
    update.message.reply_text("Hello! I'm Homework Bot!")
    updater.dispatcher.add_handler(CommandHandler('start', start))

# Healthcheck Flask app
app = Flask(__name__)

@app.route('/')
def index():
    return 'I am alive!', 200

if __name__ == '__main__':
    Thread(target=start_bot).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
