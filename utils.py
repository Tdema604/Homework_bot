import logging
import os
import pytz
from datetime import datetime
from telegram import Bot
from telegram.constants import ParseMode

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = os.environ.get("ADMIN_ID")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

bot = Bot(token=BOT_TOKEN)

def format_uptime(start_time):
    uptime = int(datetime.now().timestamp() - start_time)
    hours, remainder = divmod(uptime, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}h {minutes}m {seconds}s"

async def notify_admin_startup():
    now_btt = datetime.now(pytz.timezone("Asia/Thimphu")).strftime("%Y-%m-%d %I:%M:%S %p")
    msg = (
        "✅ <b>Homework Bot deployed and active on Render!</b>\n"
        f"🕒 <b>{now_btt} (BTT)</b>\n"
        f"🌐 <b><a href='{WEBHOOK_URL}'>Check Uptime</a></b>"
    )
    await bot.send_message(chat_id=ADMIN_ID, text=msg, parse_mode=ParseMode.HTML, disable_web_page_preview=True)

async def set_webhook():
    webhook_url = f"{WEBHOOK_URL}"
    await bot.set_webhook(url=webhook_url)
    logging.info(f"Webhook set to: {webhook_url}")
