import os
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

def load_env():
    """
    Loads environment variables from the .env file.
    """
    load_dotenv()
    logger.info("✅ Environment variables loaded.")

def is_homework(message) -> bool:
    """
    Determines whether a message is likely to be homework.
    Uses keyword heuristics and spam filtering.
    """
    if not message.text:
        return True  # Assume non-text (e.g., image, doc) is homework

    text = message.text.lower()

    # Block known spammy content
    spam_phrases = [
        "click here", "free gift", "bonus", "subscribe",
        "win", ".icu", ".xyz", "offer"
    ]
    if any(phrase in text for phrase in spam_phrases):
        return False

    # Detect homework-style content
    homework_keywords = [
        "homework", "work", "exercise", "question", "notes",
        "submit", "worksheet", "assignment", "page",
        "chapter", "topic", "due"
    ]
    score = sum(1 for keyword in homework_keywords if keyword in text)

    return score >= 2 or len(text) > 25

def get_route_map() -> dict[int, int]:
    """
    Loads the chat routing map from the ROUTE_MAP env variable.
    Example: -1001111:-1002222,-1003333:-1004444
    Returns a dictionary of source → target chat IDs.
    """
    load_dotenv()
    raw = os.getenv("ROUTE_MAP", "")
    logger.info(f"📜 RAW ROUTE_MAP: {raw}")
    route_map = {}

    for pair in raw.split(","):
        if ":" in pair:
            try:
                source, target = map(str.strip, pair.split(":"))
                route_map[int(source)] = int(target)
            except ValueError:
                logger.warning(f"⚠️ Invalid ROUTE_MAP pair ignored: {pair}")

    logger.info(f"🔁 Loaded ROUTE_MAP: {route_map}")
    return route_map