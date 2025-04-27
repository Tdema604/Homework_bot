from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import CommandHandler, MessageHandler, Filters, Application

app = Flask(__name__)

# Define your token and application
TOKEN = "your-bot-token"
application = Application.builder().token(TOKEN).build()

# Define your homework handler
def handle_homework(update: Update, context):
    homework_message = update.message.text
    print(f"Received homework message: {homework_message}")
    update.message.reply_text("Homework received!")

# Add the handler
application.add_handler(MessageHandler(Filters.ALL, handle_homework))

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    update = request.get_json()
    update_obj = Update.de_json(update, application.bot)
    application.process_update(update_obj)
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(debug=True)
