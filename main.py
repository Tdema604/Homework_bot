from flask import Flask, request
import telegram

app = Flask(__name__)

# Replace this directly with your token, or load it from environment
TOKEN = '7780579160:AAE-DWc3B6GkgMgvueHomHOF65AmciT10ac'
bot = telegram.Bot(token=TOKEN)

# Set group IDs
SOURCE_CHAT_ID = -1002570406243  # Homework group
TARGET_CHAT_ID = -1002287165008  # Parents group

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    update = telegram.Update.de_json(request.get_json(force=True), bot)

    if update.message:
        chat_id = update.message.chat.id
        message_id = update.message.message_id

        # Bot responds to /start command
        if update.message.text and update.message.text.strip() == "/start":
            bot.send_message(chat_id=chat_id, text="✅ Homework forwarder bot is active!")
            return 'ok'

        # Forward message if from homework group
        if chat_id == SOURCE_CHAT_ID:
            bot.forward_message(chat_id=TARGET_CHAT_ID, from_chat_id=chat_id, message_id=message_id)

    return 'ok'

@app.route('/')
def index():
    return '✅ Bot server is alive.'

if __name__ == '__main__':
    app.run(debug=True)
