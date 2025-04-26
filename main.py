import os
import telegram
from telegram.ext import Application, MessageHandler, filters
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Fetch configuration variables
TOKEN = os.getenv("TOKEN")
SOURCE_GROUP_ID = int(os.getenv("SOURCE_GROUP_ID"))
TARGET_CHAT_ID = int(os.getenv("TARGET_CHAT_ID"))
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))

# Debug Mode
DEBUG_MODE = False

# Initialize bot
bot = telegram.Bot(token=TOKEN)

# Define keywords for detecting homework
KEYWORDS = ["homework", "assignment", "worksheet"]

async def forward_message(update, context):
    message = update.message

    if not message:  # Extra safety check
        return

    if message.chat.id == SOURCE_GROUP_ID:
        # Combine text/caption
        text_content = message.text or message.caption or ""
        text_lower = text_content.lower()

        if any(keyword in text_lower for keyword in KEYWORDS):
            try:
                # Forward appropriate message based on type
                if message.text:
                    await bot.send_message(chat_id=TARGET_CHAT_ID, text=message.text)
                elif message.photo:
                    await bot.send_photo(chat_id=TARGET_CHAT_ID, photo=message.photo[-1].file_id, caption=message.caption or "")
                elif message.document:
                    await bot.send_document(chat_id=TARGET_CHAT_ID, document=message.document.file_id, caption=message.caption or "")

                # Notify admin gently (optional)
                await bot.send_message(chat_id=ADMIN_CHAT_ID, text="✅ Homework forwarded to parents group!")

                if DEBUG_MODE:
                    print(f"✅ Homework forwarded successfully: {text_content[:30]}...")

            except Exception as e:
                error_msg = f"⚠️ Error forwarding homework: {e}"
                await bot.send_message(chat_id=ADMIN_CHAT_ID, text=error_msg)
                if DEBUG_MODE:
                    print(error_msg)

        else:
            # Do nothing if not homework
            if DEBUG_MODE:
                print(f"ℹ️ Non-homework message ignored: {text_content[:30]}...")

# Initialize and run the bot
app = Application.builder().token(TOKEN).build()

app.add_handler(MessageHandler(filters.ALL, forward_message))

print("🚀 Bot is running cleanly... Waiting for homework messages.")
app.run_polling()