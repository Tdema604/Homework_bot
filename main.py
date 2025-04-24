from telegram.ext import Dispatcher, CommandHandler
from flask import Flask, request
from telegram import Bot, Update
import os

TOKEN = os.environ.get(7780579160:AAE-DWc3B6GkgMgvueHomHOF65AmciT10ac)
bot = Bot(token=TOKEN)
app = Flask(__name__)

dispatcher = Dispatcher(bot, None, workers=0, use_context=True)

# Example handler
def start(update, context):
    update.message.reply_text("Hello! I'm alive.")

dispatcher.add_handler(CommandHandler("start", start))

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

@app.route("/")
def index():
    return "Bot is running."

if __name__ == "__main__":
    # Set webhook URL on deploy
    bot.set_webhook(f"https://homework-tbsp.onrender.com/{TOKEN}")
    app.run(port=5000)
