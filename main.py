from flask import Flask, request
import telegram
import os

app = Flask(__name__)

# ✅ Use your actual bot token here or fetch from environment variable
TOKEN = '7780579160:AAE-DWc3B6GkgMgvueHomHOF65AmciT10ac'
bot = telegram.Bot(token=TOKEN)

# ✅ Replace with your actual group IDs
SOURCE_CHAT_ID = -1002570406243  # Student (Homework) Group
TARGET_CHAT_ID = -1002287165008  # Parents Group

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    update = telegram.Update.de_json(request.get_json(force=True), bot)
    print("🔄 Incoming update:", update)

    if update.message:
        chat_id = update.message.chat.id
        message_id = update.message.message_id
        print(f"📨 Message from chat ID {chat_id}, message ID {message_id}")

        # Respond to /start command
        if update.message.text == "/start":
            bot.send_message(chat_id=chat_id, text="✅ Bot is active!")
            return 'ok'

        # ✅ Forward message from student group to parent group
        if chat_id == SOURCE_CHAT_ID:
            bot.forward_message(
                chat_id=TARGET_CHAT_ID,
                from_chat_id=chat_id,
                message_id=message_id
            )
            print(f"✅ Message forwarded from {SOURCE_CHAT_ID} to {TARGET_CHAT_ID}")

    return 'ok'

@app.route('/')
def index():
    return '🚀 Bot is alive and running!'

if __name__ == '__main__':
    app.run(debug=True)
