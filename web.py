import logging
from flask import Flask, request, jsonify
from telegram import Update
from bot import application
from utils import load_env

# Load environment variables
load_env()

# Fetch required environment variables
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
SECRET_PATH = os.getenv("SECRET_PATH")

app = Flask(__name__)

@app.route(f'/{SECRET_PATH}', methods=['POST'])
def webhook():
    update = request.get_json()
    update_obj = Update.de_json(update, application.bot)
    application.process_update(update_obj)
    return jsonify({"status": "ok"}), 200

@app.route("/", methods=["GET"])
def index():
    return "✅ Homework Bot is running!"

# Set the webhook URL
def set_webhook():
    bot = application.bot
    secure_url = f"{WEBHOOK_URL}/{SECRET_PATH}"
    logging.info(f"Webhook set to: {secure_url}")
    bot.set_webhook(url=secure_url)
