import os
import json
import logging
import re
from dotenv import load_dotenv
from telegram import Message

# Correct logger name initialization
logger = logging.getLogger(__name__)

# Load environment variables
def load_env():
    load_dotenv()
    logger.info("Environment variables loaded.")

# Load MarkdownV2 escape function
def escape_markdown(text: str) -> str:
    if not text:
        return ""
    # Escape characters required by MarkdownV2
    escape_chars = r"_*[]()~`>#+-=|{}.!"
    return ''.join(['\\' + c if c in escape_chars else c for c in text])

# ROUTE MAP PERSISTENCE
def initialize_routes(bot_data):
    route_map = bot_data.get("ROUTE_MAP", {})
    if not isinstance(route_map, dict):
        raise ValueError("ROUTE_MAP must be a dictionary")
    
def load_routes_from_file() -> dict:
    """Load routing map from JSON file on disk."""
    if not os.path.exists(ROUTE_FILE):
        logger.warning("⚠️ No routes.json found. Starting with empty route map.")
        return {}
    try:
        with open(ROUTE_FILE, "r") as f:
            data = json.load(f)
            logger.info(f"✅ Loaded {len(data)} routes from routes.json.")
            return {int(k): v for k, v in data.items()}
    except Exception as e:
        logger.exception("🚨 Failed to load routes from file:")
        return {}

def save_routes_to_file(route_map: dict):
    """Save the routing map to a JSON file on disk."""
    try:
        with open(ROUTE_FILE, "w") as f:
            json.dump({str(k): v for k, v in route_map.items()}, f, indent=2)
        logger.info("💾 Routes saved to routes.json.")
    except Exception as e:
        logger.exception("🚨 Failed to save routes to file:")

# Enhanced homework detection with spam filtering and keyword scoring
def is_homework(message: Message) -> bool:
    if not message.text:
        return False  # Explicitly return False if no text is present

    text = message.text.lower()

    # List of phrases considered as spam
    spam_phrases = [
        "click here", "free gift", "bonus", "subscribe",
        "win", ".icu", ".xyz", "offer", "buy now", "cash prize"
    ]
    # If any of the spam phrases are found, ignore the message
    if any(phrase in text for phrase in spam_phrases):
        return False

    # Strong keywords related to homework
    strong_keywords = [
        "homework", "hw", "assignment", "classwork", "task", "work", 
    "worksheet", "project", "activity", "practice", 
    "revision", "test prep", "reading", "notes", "prep", "quiz", "exam",
    "deadline", "submission", "due", "final", "presentation", "lab report",
    "writeup", "summary", "essay", "recap", "module", "draft",
    "slides", "questions", "maths", "science", "english", "dzongkha",
    "to-do", "school stuff", "pdf", "page no", "page", "write", 
    "do this", "read", "solve", "finish", "study", "submit", 
    "📝", "📚", "✍️", "✅", "📖"

    ]
    # Weak keywords that might relate to homework
    weak_keywords = [
        "work", "read", "write", "draw", "solve", "fill",
        "copy", "prepare", "practice", "home task"
    ]

    # Count hits for strong and weak keywords
    strong_hits = sum(1 for word in strong_keywords if word in text)
    weak_hits = sum(1 for word in weak_keywords if word in text)
    total_score = (strong_hits * 2) + weak_hits

    # Specific hints like "page", "submit", "q.", etc.
    hints = ["page", "submit", "due", "q.", "ex.", "exercise", "copy this"]
    pattern_hits = sum(1 for h in hints if h in text)

    # If total score or pattern hits meet threshold, it's considered homework
    return total_score + pattern_hits >= 3 or len(text) > 50

# Define media type icons based on message content
def get_media_type_icon(message: Message) -> str:
    if message.text:
        return "📝 "  # Text message
    elif message.photo:
        return "📸 "  # Photo message
    elif message.document:
        return "📄 "  # Document message
    elif message.video:
        return "📹 "  # Video message
    elif message.voice:
        return "🎤 "  # Voice message
    else:
        return "🔁 "  # Default icon for other media types

# Function to get the route map from environment variable
def get_route_map() -> dict:
    load_dotenv()  # Load environment variables
    raw = os.getenv("ROUTE_MAP", "")  # Fetch route map from .env
    logger.info(f"RAW ROUTE_MAP: {raw}")
    route_map = {}

    for pair in raw.split(","):  # Iterate over each pair
        if ":" in pair:
            try:
                source, target = map(str.strip, pair.split(":"))
                route_map[int(source)] = int(target)  # Map source to target
            except ValueError:
                logger.warning(f"Invalid ROUTE_MAP pair ignored: {pair}")

    logger.info(f"Loaded ROUTE_MAP: {route_map}")
    return route_map