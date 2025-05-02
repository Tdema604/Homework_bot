import os
import re
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

def load_env():
    load_dotenv()
    logger.info("✅ Environment variables loaded.")

def is_homework(message):
    if not message.text:
        return True  # Non-text media is assumed to be homework

    text = message.text.lower()

    # Ignore common spam/phishing phrases
    spam_phrases = ["click here", "free gift", "bonus", "subscribe", "win", ".icu", ".xyz", "offer"]
    if any(phrase in text for phrase in spam_phrases):
        return False

    # Heuristic keywords to identify homework
    homework_keywords = ["homework", "work", "exercise", "question", "notes", "submit", "worksheet", "assignment", "page", "chapter", "topic", "due"]

    score = sum(1 for keyword in homework_keywords if keyword in text)

    if score >= 2 or len(text) > 25:
        return True

    return False

def get_route_map():
    raw = os.getenv("ROUTE_MAP", "")
    pairs = raw.split(",")
    route_map = {}

    for pair in pairs:
        if ":" in pair:
            source, target = pair.split(":")
            try:
                route_map[int(source.strip())] = int(target.strip())
            except ValueError:
                logger.warning(f"⚠️ Invalid ROUTE_MAP pair ignored: {pair}")

    logger.info(f"🔁 Loaded ROUTE_MAP: {route_map}")
    return route_map
