from telegram import Update
from telegram.ext import ContextTypes
from functools import wraps
import os

ADMIN_IDS = os.getenv("ADMIN_IDS", "").split(",")  # Ensure this is set in .env

def admin_only(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = str(update.effective_user.id)
        if user_id not in ADMIN_IDS:
            await update.message.reply_text("🚫 You are not authorized to use this command.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper
