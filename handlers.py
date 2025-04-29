# handlers.py

import os
import logging
from datetime import datetime
from pytz import timezone
from telegram import Update
from telegram.ext import ContextTypes
from utils import is_spam, get_uptime

ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
TARGET_CHAT_ID = os.getenv("TARGET_CHAT_ID")
SOURCE_CHAT_ID = os.getenv("SOURCE_CHAT_ID")

start_time = datetime.now().timestamp()

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Bot is online and ready to forward homework!")

# /status command
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uptime = get_uptime(start_time)
    await update.message.reply_text(f"✅ Bot is online.\n⏱ Uptime: {uptime}")

# Forward homework or delete spam
async def handle_homework(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        await context.bot.forward_message(
            chat_id=TARGET_CHAT_ID,
            from_chat_id=update.effective_chat.id,
            message_id=message.message_id
        )
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text="✅ Homework forwarded!")
    else:
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text="⚠️ No valid homework found.")
