# web.py

from flask import Flask, request
import asyncio
from telegram import Update
from telegram.ext import Application
from bot import application  # the Application instance from bot.py

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return "<h2>✅ Homework Forwarder Bot is Live!</h2>"

@app.route("/<path:token>", methods=["POST"])
def webhook(token):
    try:
        update = Update.de_json(request.get_json(force=True), application.bot)

        async def handle():
            await application.initialize()  # Ensure bot is fully ready
            await application.process_update(update)
            await application.shutdown()  # Optional clean-up

        asyncio.run(handle())
    except Exception as e:
        print(f"Webhook error: {e}")
        return "Error", 500

    return "OK", 200
