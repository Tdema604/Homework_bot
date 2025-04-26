from flask import Flask, request
import telegram
import os

app = Flask(__name__)

TOKEN = os.environ.get('TOKEN')
ADMIN_CHAT_ID = int(os.environ.get('ADMIN_CHAT_ID', '0'))

bot = telegram.Bot(token=TOKEN)

SOURCE_CHAT_ID = -1002570406243
TARGET_CHAT_ID = -1002287165008

HOMEWORK_KEYWORDS = ['homework', 'assignment', '#home', '#hw', 'task']
SPAM_KEYWORDS = [
    'jetonvpnbot', 'vpn', 'абсолютно', 'бесплатно', 'начать пробный период',
    'https://', 'http://', 't.me/', '@jetonvpnbot', 'IOS/Android/Windows/Mac',
    'YouTube', 'Instagram', '🔥', '❤️', '📺', '📸'
]

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    try:
        update = telegram.Update.de_json(request.get_json(force=True), bot)
        msg = update.message

        if not msg:
            return 'ok'

        chat_id = msg.chat.id
        message_id = msg.message_id
        user_id = msg.from_user.id
        text = (msg.text or "").lower()
        caption = (msg.caption or "").lower()
        is_forwarded = msg.forward_date is not None

        # Ban bots
        if msg.from_user.is_bot:
            try:
                bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
                bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"⚠️ Banned bot user in group {chat_id}")
            except Exception as e:
                print(f"[Ban Error] {e}")
            return 'ok'

        # Detect and delete spam
        if is_forwarded or any(word in text for word in SPAM_KEYWORDS) or any(word in caption for word in SPAM_KEYWORDS):
            try:
    bot.delete_message(chat_id=chat_id, message_id=message_id)
    bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"⚠️ Deleted spam in group {chat_id}")
except telegram.error.TelegramError as e:
    bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"❌ Failed to delete message in {chat_id}: {e}")
            return 'ok'

        # Start command
        if msg.text == "/start":
            bot.send_message(chat_id=chat_id, text="✅ Bot is active!")
            return 'ok'

        # Homework forwarding
        if chat_id == SOURCE_CHAT_ID and (
            any(word in text for word in HOMEWORK_KEYWORDS) or any(word in caption for word in HOMEWORK_KEYWORDS)
        ):
            bot.forward_message(chat_id=TARGET_CHAT_ID, from_chat_id=chat_id, message_id=message_id)

    except Exception as e:
        print(f"[Webhook Error] {e}")

    return 'ok'

@app.route('/')
def index():
    return 'Bot is alive!'

if __name__ == '__main__':
    app.run()
