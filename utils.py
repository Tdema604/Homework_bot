from dotenv import load_dotenv
import os

def load_env():
    load_dotenv()

def get_homework_keywords():
    raw_keywords = os.getenv("HOMEWORK_KEYWORDS", "")
    return [kw.strip().lower() for kw in raw_keywords.split(",") if kw.strip()]

def is_homework(message):
    if not message.text:
        return False
    homework_keywords = get_homework_keywords()
    return any(keyword in message.text.lower() for keyword in homework_keywords)


async def forward_homework(bot, message, target_chat_id):
    try:
        await bot.forward_message(
            chat_id=target_chat_id,
            from_chat_id=message.chat_id,
            message_id=message.message_id,
        )
    except Exception as e:
        print(f"❌ Failed to forward message: {e}")

def is_spam(message):
    spam_keywords = ['free', 'win', 'prize', 'lottery', 'cash']
    return any(keyword in message.text.lower() for keyword in spam_keywords if message.text)
def is_homework(message):
    if not message.text:
        return False

    homework_keywords = ['homework', 'hw', 'assignment', 'work', 'math', 'science', 'question', 'chapter']
    return any(keyword in message.text.lower() for keyword in homework_keywords)


async def notify_admin(bot, admin_chat_id, text):
    try:
        await bot.send_message(chat_id=admin_chat_id, text=text)
    except Exception as e:
        print(f"❌ Failed to notify admin: {e}")

def is_telegram_request(ip):
    # Temporary bypass to ensure Telegram webhook works in dev
    return True

    # Later, you can implement this properly using ipaddress module
    # import ipaddress
    # telegram_ip_ranges = [
    #     ipaddress.ip_network("149.154.160.0/20"),
    #     ipaddress.ip_network("91.108.4.0/22")
    # ]
    # client_ip = ipaddress.ip_address(ip)
    # return any(client_ip in net for net in telegram_ip_ranges)
