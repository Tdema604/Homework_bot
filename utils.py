import os
import logging
from dotenv import load_dotenv

logger = logging.getLogger(name)

def load_env():
    """
    Loads environment variables from the .env file.
    """
    load_dotenv()
    logger.info(" Environment variables loaded.")

def is_homework(message) -> bool:
    """
    Smarter homework detector using keyword scoring and pattern heuristics.
    """
    if not message.text:
        return True  # Non-text content is often homework (images, docs, etc.)

    text = message.text.lower()

    # Block known spammy content
    spam_phrases = [
        "click here", "free gift", "bonus", "subscribe",
        "win", ".icu", ".xyz", "offer", "buy now", "cash prize"
    ]
    if any(phrase in text for phrase in spam_phrases):
        return False

    # Homework keyword banks
    strong_keywords = [
        "homework", "assignment", "worksheet", "submit",
        "classwork", "question", "due", "test", "exam",
        "page", "chapter", "topic", "notes", "activity"
    ]

    weak_keywords = [
        "work", "read", "write", "draw", "solve", "fill",
        "copy", "prepare", "practice", "home task"
    ]

    # Scoring logic
    strong_hits = sum(1 for word in strong_keywords if word in text)
    weak_hits = sum(1 for word in weak_keywords if word in text)
    total_score = (strong_hits * 2) + weak_hits

    # Pattern-based hinting (e.g., "Page 15 Q.3", "submit by Monday")
    hints = ["page", "submit", "due", "q.", "ex.", "exercise", "copy this"]
    pattern_hits = sum(1 for h in hints if h in text)

    return total_score + pattern_hits >= 3 or len(text) > 50

def get_route_map() -> dict[int, int]:
    """
    Loads the chat routing map from the ROUTE_MAP env variable.
    Example: -1002604477249:-1002589235777,-1002653845682:-1002594882166
    Returns a dictionary of source  target chat IDs.
    """
    load_dotenv()
    raw = os.getenv("ROUTE_MAP", "")
    logger.info(f" RAW ROUTE_MAP: {raw}")
    route_map = {}

    for pair in raw.split(","):
        if ":" in pair:
            try:
                source, target = map(str.strip, pair.split(":"))
                route_map[int(source)] = int(target)
            except ValueError:
                logger.warning(f" Invalid ROUTE_MAP pair ignored: {pair}")

    logger.info(f" Loaded ROUTE_MAP: {route_map}")
    return route_map