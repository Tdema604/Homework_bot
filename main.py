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

# Suspicious words to block spammy messages
BLOCKED_KEYWORDS = ['vpn', '@', 'click here', 'free trial', 'instagram', 'youtube', '🔥', '💰']

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    update = telegram.Update.de_json(request.get_json(force=True), bot)

    if update.message:
        chat_id = update.message.chat.id
        message_id = update.message.message_id
        message = update.message
        text = message.text.lower() if message.text else ""
        caption = message.caption.lower() if message.caption else ""

        # Check if it's a /start command
        if message.text == "/start":
            bot.send_message(chat_id=chat_id, text="✅ Bot is active!")
            return 'ok'

        # Forward only if:
        # - Message is from source group
        # - Not a forwarded message or via another bot
        # - Contains a valid homework keyword
        # - Does not contain blocked/spammy keywords
        if chat_id == SOURCE_CHAT_ID:
            if not message.forward_date and not message.via_bot:
                if (any(kw in text for kw in HOMEWORK_KEYWORDS) or
                    any(kw in caption for kw in HOMEWORK_KEYWORDS)):
                    
                    # Block message if it contains spammy keywords
                    if not any(bad_kw in text for bad_kw in BLOCKED_KEYWORDS) and \
                       not any(bad_kw in caption for bad_kw in BLOCKED_KEYWORDS):
                        
                        bot.forward_message(chat_id=TARGET_CHAT_ID, from_chat_id=chat_id, message_id=message_id)

    return 'ok'

@app.route('/')
def index():
    return 'Bot is alive!'

if __name__ == '__main__':
    app.run()