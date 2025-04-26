from flask import Flask, request
import telegram
import os

app = Flask(__name__)
TOKEN = os.environ['TOKEN']
bot = telegram.Bot(token=TOKEN)

SOURCE_CHAT_ID = -1002570406243  # Homework group
TARGET_CHAT_ID = -1002287165008  # Parents group

# Keywords to identify homework-related messages
HOMEWORK_KEYWORDS = ['homework', 'assignment', '#home', '#hw', 'task']

# Keywords to identify spam messages (add more if needed)
SPAM_KEYWORDS = ['vpn', '@jetonvpnbot', 'бесплатно', '🔥', '❤️', 'https://t.me/JetonVPNbot']

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    update = telegram.Update.de_json(request.get_json(force=True), bot)

    if update.message:
        chat_id = update.message.chat.id
        message_id = update.message.message_id
        text = update.message.text.lower() if update.message.text else ""
        caption = update.message.caption.lower() if update.message.caption else ""
        user = update.message.from_user

        # Block bot accounts
        if user.is_bot:
            try:
                bot.ban_chat_member(chat_id=chat_id, user_id=user.id)
                return 'ok'
            except:
                return 'ok'

        # Delete spam messages
        if any(keyword in text for keyword in SPAM_KEYWORDS) or any(keyword in caption for keyword in SPAM_KEYWORDS):
            try:
                bot.delete_message(chat_id=chat_id, message_id=message_id)
            except:
                pass
            return 'ok'

        # Only forward if it's from source and contains homework keyword
        if chat_id == SOURCE_CHAT_ID:
            if any(keyword in text for keyword in HOMEWORK_KEYWORDS) or \
               any(keyword in caption for keyword in HOMEWORK_KEYWORDS):
                bot.forward_message(chat_id=TARGET_CHAT_ID, from_chat_id=chat_id, message_id=message_id)

    return 'ok'

@app.route('/')
def index():
    return 'Bot is alive!'

if __name__ == '__main__':
    app.run()
