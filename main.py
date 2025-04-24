from flask import Flask, request
import telegram
import os

app = Flask(__name__)

# Use the environment variable for the token
TOKEN = os.environ.get('TOKEN')  # Ensure to set the TOKEN environment variable in Render
bot = telegram.Bot(token=TOKEN)

# Chat IDs
SOURCE_CHAT_ID = -1002570406243  # Homework group
TARGET_CHAT_ID = -1002287165008  # Parents group

# Webhook endpoint that will receive updates
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    update = telegram.Update.de_json(request.get_json(force=True), bot)
    
    if update.message:
        chat_id = update.message.chat.id
        message_id = update.message.message_id

        # Check if the /start command was sent
        if update.message.text == "/start":
            bot.send_message(chat_id=chat_id, text="✅ Bot is active!")
            return 'ok'

        # Forward message if it's from the homework group
        if chat_id == SOURCE_CHAT_ID:
            bot.forward_message(chat_id=TARGET_CHAT_ID, from_chat_id=chat_id, message_id=message_id)

    return 'ok'

# Index route to check if the bot is alive
@app.route('/')
def index():
    return 'Bot is alive!'

# Start the Flask app
if __name__ == '__main__':
    # Render uses port from environment, so ensure it's handled properly
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
                                                    
