from flask import Flask, request
import telegram
import os

app = Flask(__name__)
TOKEN = os.environ['BOT_TOKEN']
bot = telegram.Bot(token=TOKEN)

# Replace with your actual group/chat IDs
SOURCE_CHAT_ID = -1002570406243  # Homework group
TARGET_CHAT_ID = -1002287165008  # Parents group

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    update = telegram.Update.de_json(request.get_json(force=True), bot)
    print("Received update:", update)

    if update.message:
        chat_id = update.message.chat.id
        message_text = update.message.text or ""
        message_id = update.message.message_id

        print("Message from chat:", chat_id, "| Text:", message_text)

        # Respond to /start from any chat
        if message_text == "/start":
            bot.send_message(chat_id=chat_id, text="✅ Bot is active!")
            return 'ok'

        # Forward only if it's from the homework group and contains keyword
        if chat_id == SOURCE_CHAT_ID:
            lower_text = message_text.lower()
            if any(word in lower_text for word in ["homework", "worksheet", "assignment"]):
                bot.forward_message(chat_id=TARGET_CHAT_ID, from_chat_id=chat_id, message_id=message_id)
                print("✅ Forwarded to Parents Group.")
            else:
                print("❌ No keyword match. Message not forwarded.")
    else:
        print("No message found in update.")

    return 'ok'

@app.route('/')
def index():
    return 'Bot is alive!'

if __name__ == '__main__':
    app.run(debug=True)
