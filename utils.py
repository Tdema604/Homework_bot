import os
from dotenv import load_dotenv

# Load environment variables
def load_env():
    load_dotenv()

# Anti-spam filter
def is_spam(text):
    SPAM_KEYWORDS = [
        "free", "click here", "buy now", "limited time", "offer", "deal", "visit", "subscribe",
        "discount", "promotion", "win big", "urgent", "vpn", "trial", "access", "claim", "winning"
    ]
    return any(word in text.lower() for word in SPAM_KEYWORDS)
