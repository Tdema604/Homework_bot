from telegram import Update, MessageEntity
from telegram.ext import ContextTypes
from utils import is_spam, forward_homework, notify_admin
import logging

logger = logging.getLogger(__name__)

STUDENT_GROUP_ID = -1002604477249  # Replace with your actual student group ID
PARENT_GROUP_ID = -1002589235777   # Replace with your actual parent group ID
ADMIN_USER_ID = 740241927          # Your admin Telegram user ID

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message:
        return

    # Only process messages from the student group
    if message.chat_id != STUDENT_GROUP_ID:
        return

    try:
        if is_spam(message):
            await message.delete()
            await notify_admin(context.bot, ADMIN_USER_ID, "⚠️ Spam message deleted from student group.")
            return

        # Forward to parent group
        await forward_homework(context.bot, message, PARENT_GROUP_ID)
        await notify_admin(context.bot, ADMIN_USER_ID, "✅ Homework message forwarded successfully.")
        
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        await notify_admin(context.bot, ADMIN_USER_ID, f"❌ Error: {e}")
