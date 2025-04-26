from flask import Flask, request
import telegram
import os
import re

app = Flask(__name__)
TOKEN = os.environ.get('TOKEN')
ADMIN_CHAT_ID = int(os.environ.get('ADMIN_CHAT_ID', '0'))

bot = telegram.Bot(token=TOKEN)

SOURCE_CHAT_ID = -1002570406243
TARGET_CHAT_ID = -1002287165008

HOMEWORK_KEYWORDS = ['homework', 'assignment', '#home', '#hw', 'task']
SPAM_KEYWORDS = [
    'jetonvpnbot', 'vpn', 'absolutely free', 'начать пробный период',
    'бесплатно', 'IOS/Android/Windows/Mac', 'YouTube 🚀', 'Instagram ⚡️'
]

# Regex pattern to detect URLs
URL_REGEX = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'

# Spam emojis list to detect in messages
SPAM_EMOJIS = ['🔥', '❤️', '📺', '📸']

# Function to check if a message is spam
def is_spam(message):
    message_lower = message.lower()  # Ensure case insensitivity

    # Check if any spam keyword is in the message
    for keyword in SPAM_KEYWORDS:
        if keyword.lower() in message_lower:
            return True

    # Check if URL is present in the message
    if re.search(URL_REGEX, message):
        return True

    # Check if any spam emoji is in the message
    for emoji in SPAM_EMOJIS:
        if emoji in message:
            return True

    return False

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

        # If the message is from a bot, ban the user
        if update.message.from_user.is_bot:
            try:
                bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
                bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"⚠️ Banned a bot user from group {chat_id}")
            except Exception as e:
                bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"❌ Failed to ban user: {e}")
            return 'ok'

        # Check if the message contains spam
        if is_spam(text) or is_spam(caption) or is_forwarded:
            try:
                bot.delete_message(chat_id=chat_id, message_id=message_id)
                bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"⚠️ Deleted spam in group {chat_id}")
            except telegram.error.TelegramError as e:
                bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"❌ Failed to delete message in {chat_id}: {e}")
            return 'ok'

        # If the user types "/start"
        if update.message.text == "/start":
            bot.send_message(chat_id=chat_id, text="✅ Bot is active!")
            return 'ok'

        # Forward homework messages
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
