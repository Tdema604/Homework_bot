from flask import Flask, request
import telegram
import os

app = Flask(__name__)
TOKEN = os.environ['TOKEN']  # TOKEN set in environment variable
bot = telegram.Bot(token=TOKEN)

# Replace with your actual chat IDs
SOURCE_CHAT_ID = -1002570406243  # Student Group
TARGET_CHAT_ID = -1002287165008  # Parents Group

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    update = telegram.Update.de_json(request.get_json(force=True), bot)

    if update.message:
        chat_id = update.message.chat.id
        message_id = update.message.message_id

        if update.message.text == "/start":
            bot.send_message(chat_id=chat_id, text="✅ Bot is active and forwarding!")
            return 'ok'

        if chat_id == SOURCE_CHAT_ID:
            bot.forward_message(chat_id=TARGET_CHAT_ID, from_chat_id=chat_id, message_id=message_id)

    return 'ok'

@app.route('/')
def index():
    return 'Bot is alive!'
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)


# DO NOT include app.run() — Gunicorn will handle that
