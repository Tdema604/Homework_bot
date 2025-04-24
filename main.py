from flask import Flask, request
import telegram
import os

app = Flask(__name__)
TOKEN = os.environ["7780579160:AAE-DWc3B6GkgMgvueHomHOF65AmciT10ac"]
bot = telegram.Bot(token=TOKEN)

# Replace with your actual group/chat IDs
SOURCE_CHAT_ID = -4703962156  # Student group
TARGET_CHAT_ID = -1002287165008  # Parents group

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    update = telegram.Update.de_json(request.get_json(force=True), bot)

    if update.message:
        chat_id = update.message.chat.id
        message_text = update.message.text
        message_id = update.message.message_id

        # ✅ Respond to /start from any chat
        if message_text == "/start":
            bot.send_message(chat_id=chat_id, text="✅ Bot is active! Send a message in the student group to test forwarding.")
            return 'ok'

        # ✅ Forward only from the student group
        if chat_id == SOURCE_CHAT_ID:
            bot.forward_message(chat_id=TARGET_CHAT_ID, from_chat_id=chat_id, message_id=message_id)

    return 'ok'

@app.route('/')
def index():
    return 'Bot is alive!'

if __name__ == '__main__':
    app.run(debug=True)
