import os
import logging
import re
import json
import pytesseract
from PIL import Image
from telegram import Message
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

# Initialize the model once at the top level (so it doesn't reload every time)
model = WhisperModel("base", compute_type="int8")

# Add this line to point to Tesseract on Windows
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def get_target_group_id(routes_map: dict, source_chat_id: int) -> int | None:
    """
    This function is similar to `get_forward_target` and could serve as an alias or custom approach.
    It checks if a source chat ID is in the routes map and returns the corresponding target ID.
    """
    return routes_map.get(str(source_chat_id))  # Ensure to use str if the keys are stored as strings


def transcribe_audio_with_whisper(file_path: str) -> str:
    try:
        segments, _ = model.transcribe(file_path)
        text = " ".join(segment.text for segment in segments if segment.text)
        return text.strip()
    except Exception as e:
        logger.error(f"Whisper transcription failed: {e}")
        return ""


def get_forward_target(routes_map: dict, source_chat_id: int) -> int | None:
    """
    Returns the destination chat ID if the source chat ID is in routes_map.
    Otherwise, returns None.
    """
    return routes_map.get(str(source_chat_id))  # Use str because keys are strings in .env


def extract_text_from_image(image_path):
    try:
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img)
        return text.strip()
    except Exception as e:
        return f"OCR error: {str(e)}"

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
    if is_render_env():
        raw = os.getenv("ROUTES_MAP", "")
        logger.info(f"📦 Loading ROUTES_MAP from Render env: {raw}")
    else:
        raw = os.getenv("ROUTES_MAP", "")
        logger.info(f"📦 Loading ROUTES_MAP from .env: {raw}")

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
    # Retrieve the environment variable
    raw = os.getenv("ADMIN_IDS", "")
    
    if not raw:
        # If the variable is missing or empty, log a warning
        logger.warning("⚠️ ADMIN_IDS environment variable is missing or empty.")
        return set()
    
    logger.warning(f"⚠️ ADMIN_IDS environment variable is loaded: {raw}")

    try:
        # Convert the comma-separated string of IDs into a set of integers
        admin_ids = set(int(x.strip()) for x in raw.split(",") if x.strip().isdigit())
    except ValueError:
        # If parsing fails, log the error and return an empty set
        logger.error("❌ Failed to parse ADMIN_IDS. Please check format.")
        return set()

    # Log the successfully loaded admin IDs
    logger.warning(f"✅ Loaded ADMIN_IDS: {admin_ids}")
    return admin_ids

def load_routes_from_env() -> dict:
    """
    Load route mappings from the ROUTES_MAP environment variable.
    Format: "123:456,789:1011"
    """
    raw = os.getenv("ROUTES_MAP", "")
    logger.info(f"📦 Loading ROUTES_MAP: {raw}")

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

def save_routes_to_env(routes_map: dict):
    """
    Save routes map back into memory (os.environ) in the same format.
    This does NOT persist to disk. For development/testing only.
    """
    os.environ["ROUTES_MAP"] = ",".join(f"{k}:{v}" for k, v in routes_map.items())
    logger.info("📝 Updated in-memory ROUTES_MAP (won’t persist to .env)")


# === HOMEWORK DETECTION ===
def is_homework_like (message: str) -> bool:
    if not message.text:
        return False

    text = text.lower()

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
    return any(word in text for word in keywords)


# Define media type icons based on message content

def get_media_type_icon(message: Message) -> str:
    if message.photo:
        return "🖼️"
    elif message.document:
        return "📄"
    elif message.video:
        return "🎞️"
    elif message.audio:
        return "🎵"
    elif message.voice:
        return "🎤"
    elif message.sticker:
        return "🔖"
    elif message.text:
        return "✏️"
    return "📎"

async def forward_message_to_parents(message, routes_map):
    # Get the source chat id (where the message is coming from)
    source_chat_id = message.chat.id
    # Get destination group ids (where the message will be forwarded)
    dest_ids = routes_map.get(str(source_chat_id))
    
    if not dest_ids:
        return  # If no routes exist for this chat id, don't do anything

    for dest_id in dest_ids:
        try:
            await message.forward(chat_id=int(dest_id))  # Forward the message
        except Exception as e:
            print(f"Failed to forward message to {dest_id}: {e}")

def escape_markdown(text: str) -> str:
    """
    Escape MarkdownV2 special characters for safe message formatting.
    """
    escape_chars = r'\_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)