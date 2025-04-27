import os
import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# Fetch sensitive information from environment variables (SECURE)
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))
TARGET_CHAT_ID = int(os.getenv("TARGET_CHAT_ID"))

print("Bot Token:", TOKEN)
print("Admin Chat ID:", ADMIN_CHAT_ID)
print("Target Chat ID:", TARGET_CHAT_ID)

print(f"Loaded BOT TOKEN: {TOKEN}")

# Define list of spam words (can add more later)
SPAM_WORDS = ['buy now', 'free', 'click here', 'subscribe', 'promotion', 'offer']

# Start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Hello! I'm your Homework Forwarder Bot!")

# Handle All Messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return  # Safety check

    message = update.message
    text = message.text or ""
    caption = message.caption or ""

    # Combine text and caption for spam filtering
    combined_content = (text + " " + caption).lower()

    # Check for spam
    if any(word in combined_content for word in SPAM_WORDS):
        try:
            await message.delete()
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"🚨 [Spam Deleted]\nFrom: @{message.from_user.username or message.from_user.id}\nContent: {combined_content[:50]}..."
            )
        except Exception as e:
            print(f"Error deleting spam message: {e}")
        return

    # Check for Homework keyword
    if 'homework' in combined_content:
        try:
            # Forward text message
            if text:
                await context.bot.send_message(
                    chat_id=TARGET_CHAT_ID,
                    text=f"📚 Homework:\n\n{text}"
                )
            # Forward files (Images, PDFs, Word Docs, etc.)
            elif message.document or message.photo or message.video:
                if message.document:
                    await context.bot.send_document(
                        chat_id=TARGET_CHAT_ID,
                        document=message.document.file_id,
                        caption=caption or "📚 Homework Document"
                    )
                elif message.photo:
                    await context.bot.send_photo(
                        chat_id=TARGET_CHAT_ID,
                        photo=message.photo[-1].file_id,
                        caption=caption or "📚 Homework Photo"
                    )
                elif message.video:
                    await context.bot.send_video(
                        chat_id=TARGET_CHAT_ID,
                        video=message.video.file_id,
                        caption=caption or "📚 Homework Video"
                    )

            # Notify Admin about forwarded homework
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"✅ [Homework Forwarded]\nFrom: @{message.from_user.username or message.from_user.id}\nContent: {combined_content[:50]}..."
            )
        except Exception as e:
            print(f"Error forwarding homework: {e}")

# Main function
async def main():
    # Create bot application
    app = ApplicationBuilder().token(TOKEN).build()

    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.ALL, handle_message))

    # Start bot
    print("🚀 Bot is running...")
    await app.run_polling()

# Launch
if __name__ == "__main__":
    asyncio.run(main())
