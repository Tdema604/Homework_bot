from telegram import Update
from telegram.ext import CommandHandler, MessageHandler, filters
from utils import is_spam
from bot import application, ADMIN_CHAT_ID, TARGET_CHAT_ID, SOURCE_CHAT_ID

# Command to start the bot
async def start(update: Update, context):
    await update.message.reply_text("👋 Bot is online and ready to forward homework!")

# Function to handle incoming homework messages
async def handle_homework(update: Update, context):
    message = update.message
    if not message:
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text="⚠️ Empty message received.")
        return

    if update.effective_chat.id != int(SOURCE_CHAT_ID):
        await message.delete()
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text="⚠️ Message rejected. Not from a trusted group.")
        return

    if message.text and is_spam(message.text):
        await message.delete()
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"🚨 Spam deleted: {message.text[:100]}")
        return

    if message.text and "homework" in message.text.lower() or message.document or message.photo or message.video:
        await context.bot.forward_message(chat_id=TARGET_CHAT_ID, from_chat_id=update.effective_chat.id, message_id=message.message_id)
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"✅ Homework forwarded from {update.effective_chat.title or update.effective_chat.id}")
    else:
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text="⚠️ No valid homework found.")

# Register handlers
def register_handlers():
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.ALL, handle_homework))
