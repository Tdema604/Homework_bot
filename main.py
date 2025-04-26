from flask import Flask, request
import telegram
import os

app = Flask(__name__)
TOKEN = os.environ.get('TOKEN')
ADMIN_CHAT_ID = int(os.environ.get('ADMIN_CHAT_ID', '0'))

bot = telegram.Bot(token=TOKEN)

# Hardcoded for now
SOURCE_CHAT_ID = -1002570406243
TARGET_CHAT_ID = -1002287165008

HOMEWORK_KEYWORDS = ['homework', 'assignment', '#home', '#hw', 'task']
SPAM_KEYWORDS = [
    'jetonvpnbot', 'vpn', 'absolutely free', '🔥', '❤️', '📺', '📸',
    'https://', 'http://', 't.me/', '@jetonvpnbot', 'начать пробный период',
    'бесплатно', 'IOS/Android/Windows/Mac', 'YouTube 🚀', 'Instagram ⚡️'
]

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    update = telegram.Update.de_json(request.get_json(force=True), bot)

    if update.message:
        chat_id = update.message.chat.id
        message_id = update.message.message_id
        user_id = update.message.from_user.id
        text = update.message.text.lower() if update.message.text else ""
        caption = update.message.caption.lower() if update.message.caption else ""
        is_forwarded = update.message.forward_date is not None

        if update.message.from_user.is_bot:
            try:
                bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
                bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"⚠️ Banned a bot user from group {chat_id}")
            except Exception as e:
                print(f"Ban error: {e}")
            return 'ok'

        spam_detected = any(keyword in text for keyword in SPAM_KEYWORDS) or \
                        any(keyword in caption for keyword in SPAM_KEYWORDS) or \
                        is_forwarded

        if spam_detected:
            try:
                bot.delete_message(chat_id=chat_id, message_id=message_id)
                bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"⚠️ Deleted spam in group {chat_id}")
            except Exception as e:
                print(f"Delete error: {e}")
            return 'ok'

        if update.message.text == "/start":
            bot.send_message(chat_id=chat_id, text="✅ Bot is active!")
            return 'ok'

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
