import os
import logging
from telegram import Message
import re
import os
import json

logger = logging.getLogger(__name__)

# === ROUTE MAP UTILITIES ===
def is_render_env() -> bool:
    """
    Detect if running on Render based on the presence of Render-specific environment variable.
    """
    return os.getenv("RENDER", "").lower() == "true"


def get_routes_map() -> dict:
    """
    Load route mappings from ROUTES_MAP environment variable.
    Format: "123:456,789:1011"
    """
    raw = os.getenv("ROUTES_MAP", "")
    logger.info(f"📦 Loading ROUTES_MAP from {'Render env' if is_render_env() else '.env'}: {raw}")

    routes_map = {}
    for pair in raw.split(","):
        if ":" in pair:
            try:
                source, target = map(str.strip, pair.split(":"))
                routes_map[int(source)] = int(target)
            except ValueError:
                logger.warning(f"⚠️ Invalid ROUTES_MAP pair ignored: {pair}")

    logger.info(f"✅ Parsed ROUTES_MAP: {routes_map}")
    return routes_map


def get_admin_ids() -> set[int]:
    """
    Load admin user IDs from ADMIN_IDS environment variable.
    Format: "123456,78910"
    """
    raw = os.getenv("ADMIN_IDS", "")
    logger.warning(f"⚠️ ADMIN_IDS environment variable is {'missing' if not raw else 'loaded'}: {raw}")

    try:
        admin_ids = set(int(x.strip()) for x in raw.split(",") if x.strip().isdigit())
    except ValueError:
        logger.error("❌ Failed to parse ADMIN_IDS. Please check format.")
        admin_ids = set()

    logger.warning(f"✅ Loaded ADMIN_IDS: {admin_ids}")
    return admin_ids

def save_routes_to_env(routes_map: dict):
    """
    Save routes map back into memory (os.environ) in the same format.
    This does NOT persist to disk. For development/testing only.
    """
    os.environ["ROUTES_MAP"] = ",".join(f"{k}:{v}" for k, v in routes_map.items())
    logger.info("📝 Updated in-memory ROUTES_MAP (won’t persist to .env)")

def escape_markdown(text: str) -> str:
    """
    Escape MarkdownV2 special characters for safe message formatting.
    """
    escape_chars = r'\_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)


# === HOMEWORK DETECTION ===
def is_homework(message: Message) -> bool:
    if not message.text:
        return False

    text = message.text.lower()

    spam_phrases = [
        "click here", "free gift", "bonus", "subscribe",
        "win", ".icu", ".xyz", "offer", "buy now", "cash prize"
    ]
    if any(phrase in text for phrase in spam_phrases):
        return False

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

    weak_keywords = [
        "work", "read", "write", "draw", "solve", "fill",
        "copy", "prepare", "practice", "home task"
    ]

    strong_hits = sum(1 for word in strong_keywords if word in text)
    weak_hits = sum(1 for word in weak_keywords if word in text)
    total_score = (strong_hits * 2) + weak_hits

    hints = ["page", "submit", "due", "q.", "ex.", "exercise", "copy this"]
    pattern_hits = sum(1 for h in hints if h in text)

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
