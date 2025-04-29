# utils.py
import logging
from datetime import datetime
from pytz import timezone

async def notify_admin_startup(application, ADMIN_CHAT_ID, WEBHOOK_URL):
    try:
        bt_time = datetime.now(timezone("Asia/Thimphu")).strftime("%Y-%m-%d %I:%M:%S %p (BTT)")
        status_url = f"https://{WEBHOOK_URL.replace('https://', '').split('/')[0]}"
        await application.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"✅ Homework Bot deployed and active on Render!\n🕒 {bt_time}\n🌐 [Check Uptime]({status_url})",
            parse_mode="Markdown"
        )
    except Exception as e:
        logging.error(f"Failed to notify admin on startup: {e}")
