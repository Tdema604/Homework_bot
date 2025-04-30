# handlers.py

from telegram import Update
from telegram.ext import ContextTypes
from utils import is_spam, forward_homework, notify_admin

async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    source_chat_id = context.bot_data["SOURCE_CHAT_ID"]
    target_chat_id = context.bot_data["TARGET_CHAT_ID"]
    admin_chat_id = context.bot_data["ADMIN_CHAT_ID"]

    message = update.effective_message

    # Only handle messages from the source group
    if message.chat_id != source_chat_id:
        return

    if await is_spam(message):
        await message.delete()
        await notify_admin(context.bot, admin_chat_id, "🛑 Spam message deleted.")
    else:
        await forward_homework(context.bot, message, target_chat_id)
        await notify_admin(context.bot, admin_chat_id, "✅ Homework forwarded successfully.")
# No need to add __all__, just ensure forward_message exists and is not commented

