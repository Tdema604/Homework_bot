import os
import telegram
from telegram import Update
from telegram.ext import Application, MessageHandler, filters
from telegram.ext import CommandHandler, CallbackContext
from dotenv import load_dotenv
from flask import Flask, request
import logging

# Load environment variables
load_dotenv()

# Fetch environment variables
TOKEN = os.getenv("TOKEN")
SOURCE_GROUP_ID = int(os.getenv("SOURCE_GROUP_ID"))
TARGET_CHAT_ID = int(os.getenv("TARGET_CHAT_ID"))
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))

# Initialize bot
bot = telegram.Bot(token=TOKEN)

# Flask app for Render health check
app_flask = Flask('')

@app_flask.route('/')
def home():
    return "Bot is running!"

# Webhook handler function
@app_flask.route('/' + TOKEN, methods=['POST'])
def webhook():
    json_str = request.get_data().decode("UTF-8")
    update = telegram.Update.de_json(json_str, bot)
    
    # Message forwarding logic
    message = update.message
    if message.chat.id == SOURCE_GROUP_ID:
        if message.text and any(keyword.lower() in message.text.lower() for keyword in ["homework", "assignment", "worksheet"]):
            bot.send_message(chat_id=TARGET_CHAT_ID, text=message.text)
        elif message.photo:
            if message.caption and any(keyword.lower() in message.caption.lower() for keyword in ["homework", "assignment", "worksheet"]):
                bot.send_photo(chat_id=TARGET_CHAT_ID, photo=message.photo[-1].file_id, caption=message.caption)
        elif message.document:
            if message.caption and any(keyword.lower() in message.caption.lower() for keyword in ["homework", "assignment", "worksheet"]):
                bot.send_document(chat_id=TARGET_CHAT_ID, document=message.document.file_id, caption=message.caption)
        else:
            print("⚡ Non-homework message detected, ignoring...")
    return "OK"

# Set up webhook
def set_webhook():
    url = f'https://your-render-app-url/{TOKEN}'  # Replace with your Render app URL
    bot.set_webhook(url)

if __name__ == '__main__':
    # Set the webhook when starting the app
    set_webhook()
    
    # Start Flask app (for health check and handling webhook requests)
    port = int(os.environ.get('PORT', 5000))
    app_flask.run(host="0.0.0.0", port=port)
