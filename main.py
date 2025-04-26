from flask import Flask, request
import telegram
import os

app = Flask(__name__)

TOKEN = os.environ['TOKEN']
bot = telegram.Bot(token=TOKEN)

SOURCE_CHAT_ID = -1002570406243  # Homework group
TARGET_CHAT_ID = -1002287165008  # Parents group
ADMIN_CHAT_ID = int(os.environ.get('ADMIN_CHAT_ID', '0'))  # Your Telegram user ID

# Keywords to identify homework-related messages
HOMEWORK_KEYWORDS = ['homework', 'assignment', '#home', '#hw', 'task']

# Keywords to identify spam or VPN promotions
SPAM_KEYWORDS = ['vpn', 'jetonvpn', '🔥@jetonvpnbot', '7 дней абсолютно бесплатно', '📺 youtube', '📸 instagram']

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    update = telegram.Update.de_json(request.get_json(force=True), bot)

    if update.message:
        chat_id = update.message.chat.id
        message_id = update.message.message_id
        user = update.message.from_user
        text = update.message.text.lower() if update.message.text else ""
        caption = update.message.caption.lower() if update.message.caption else ""

        # 1. /start command
        if update.message.text == "/start":
            bot.send_message(chat_id=chat_id, text="✅ Bot is active!")
            return 'ok'

        # 2. Block bot users
        if user.is_bot:
            try:
                bot.ban_chat_member(chat_id=chat_id, user_id=user.id)
                if ADMIN_CHAT_ID:
                    bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"⚠️ Banned a bot user in group {chat_id}")
            except:
                pass
            return 'ok'

        # 3. Delete spam messages
        if any(keyword in text for keyword in SPAM_KEYWORDS) or any(keyword in caption for keyword in SPAM_KEYWORDS):
            try:
                bot.delete_message(chat_id=chat_id, message_id=message_id)
                if ADMIN_CHAT_ID:
                    bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"🛡️ Deleted spam message in group {chat_id}")
            except:
                pass
            return 'ok'

        # 4. Forward homework messages
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
