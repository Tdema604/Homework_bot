# web.py

import os
import logging
import hashlib
from flask import Flask, request, jsonify
from telegram import Update
from bot import application  # Make sure this comes from bot.py

# Generate secret webhook path
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SECRET_PATH = hashlib.sha256(TOKEN.encode()).hexdigest()

# Flask app
app = Flask(__name__)

@app.route(f"/{SECRET_PATH}", methods=["POST"])
def webhook():
    update = request.get_json(force=True)
    update_obj = Update.de_json(update, application.bot)
    application.process_update(update_obj)
    return jsonify({"status": "ok"}), 200

@app.route("/", methods=["GET"])
def index():
    return """
    <html>
        <head><title>📘 Homework Forwarder Bot</title></head>
        <body style="font-family:sans-serif;text-align:center;padding-top:50px;">
            <h1>✅ Bot is running</h1>
            <p>Developed with ❤️ for Meto & Lhaki</p>
        </body>
    </html>
    """

def get_webhook_url():
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")
    return f"{WEBHOOK_URL}/{SECRET_PATH}"
