import os
import asyncio
import hashlib
from telegram.ext import ApplicationBuilder

# 🔐 Environment variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# 🔐 Secure webhook path
SECRET_PATH = hashlib.sha256(TOKEN.encode()).hexdigest()

async def set_webhook():
    application = ApplicationBuilder().token(TOKEN).build()
    secure_url = f"{WEBHOOK_URL}/{SECRET_PATH}"
    success = await application.bot.set_webhook(url=secure_url)
    
    if success:
        print("✅ Webhook set successfully!")
    else:
        print("❌ Failed to set webhook.")

if __name__ == "__main__":
    asyncio.run(set_webhook())
