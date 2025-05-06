import asyncio
from telegram.ext import Application
from main import start  # or import your application setup here
from dotenv import load_dotenv
import os

load_dotenv()
TOKEN = os.getenv("TOKEN")
print(f"Loaded TOKEN = {TOKEN}")  # Add this line for debug

async def main():
    application = Application.builder().token(TOKEN).build()

    # Add handlers here
    application.add_handler(start)  # Make sure `start` is a handler object

    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
