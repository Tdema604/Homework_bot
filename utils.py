import os
from dotenv import load_dotenv

def load_env():
    """Loads environment variables from a .env file."""
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    load_dotenv(dotenv_path=env_path)

def is_spam(message):
    suspicious_keywords = ["free", "win", "click here", "offer", "promotion", "crypto", "telegram.me/", "t.me/"]
    text = message.text or message.caption or ""

    return any(word.lower() in text.lower() for word in suspicious_keywords)
