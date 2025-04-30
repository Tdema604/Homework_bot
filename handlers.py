from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Keywords for valid homework detection
HOMEWORK_KEYWORDS = ["homework", "assignment", "worksheet"]

# Keywords commonly used in spam
SPAM_KEYWORDS = [
    "free", "bit.ly", "t.me/joinchat", "airdrop", "bonus", "investment",
    "click here", "promo", "earn", "crypto", "guaranteed", "100%", "giveaway"
]

# Main message handler
async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    # Only process messages from the source group
    if message.chat.id != context.bot_data["SOURCE_CHAT_ID"]:
        return

    text_content = message.text or message.caption or ""
    text_lower = text_content.lower()

    # Check for spam
    if any(spam in text_lower for spam in SPAM_KEYWORDS):
        try:
            await message.delete()
            logger.warning(f"🚫 Spam deleted: {text_content[:30]}...")
            await context.bot.send_message(chat_id=context.bot_data["ADMIN_CHAT_ID"],
                                           text=f"🚫 Spam blocked and deleted:\n{text_content[:50]}...")
        except Exception as e:
            logger.error(f"❌ Failed to delete spam: {e}")
        return

    # Check for homework keywords
    if any(kw in text_lower for kw in HOMEWORK_KEYWORDS):
        try:
            if message.text:
                await context.bot.send_message(chat_id=context.bot_data["TARGET_CHAT_ID"], text=message.text)
            elif message.photo:
                await context.bot.send_photo(chat_id=context.bot_data["TARGET_CHAT_ID"],
                                             photo=message.photo[-1].file_id,
                                             caption=message.caption or "")
            elif message.document:
                await context.bot.send_document(chat_id=context.bot_data["TARGET_CHAT_ID"],
                                                document=message.document.file_id,
                                                caption=message.caption or "")

            logger.info(f"✅ Forwarded: {text_content[:30]}...")
            await context.bot.send_message(chat_id=context.bot_data["ADMIN_CHAT_ID"],
                                           text=f"✅ Homework forwarded:\n{text_content[:50]}...")
        except Exception as e:
            logger.error(f"❌ Error forwarding: {e}")
            await context.bot.send_message(chat_id=context.bot_data["ADMIN_CHAT_ID"],
                                           text=f"⚠️ Error forwarding message:\n{e}")
    else:
        logger.info(f"ℹ️ Non-homework message skipped: {text_content[:30]}...")
