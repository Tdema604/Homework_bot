# utils.py

import hashlib
import time

SPAM_KEYWORDS = [
    "free", "click here", "buy now", "limited time", "offer", "deal", "visit", "subscribe",
    "discount", "promotion", "win big", "urgent", "vpn", "trial", "access", "claim", "winning"
]

def is_spam(text: str) -> bool:
    return any(word in text.lower() for word in SPAM_KEYWORDS)

def generate_secret_path(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

def get_uptime(start_time):
    uptime_seconds = int(time.time() - start_time)
    hours, remainder = divmod(uptime_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}h {minutes}m {seconds}s"
