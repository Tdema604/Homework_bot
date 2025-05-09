import os
import logging
import re
import pytesseract
from PIL import Image
from telegram import Message
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

# Initialize Whisper model once
model = WhisperModel("base", compute_type="int8")

# Windows users: set path to Tesseract executable
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# === ROUTING UTILITIES ===
def get_target_group_id(routes_map: dict, source_chat_id: int) -> int | None:
    return routes_map.get(str(source_chat_id))

def get_forward_target(routes_map: dict, source_chat_id: int) -> int | None:
    return routes_map.get(str(source_chat_id))

def is_render_env() -> bool:
    return os.getenv("RENDER", "").lower() == "true"

def get_routes_map() -> dict:
    raw = os.getenv("ROUTES_MAP", "")
    logger.info(f"\U0001F4E6 Loading ROUTES_MAP: {raw}")
    routes_map = {}
    for pair in raw.split(","):
        if ":" in pair:
            try:
                source, target = map(str.strip, pair.split(":"))
                routes_map[int(source)] = int(target)
            except ValueError:
                logger.warning(f"\u26A0\uFE0F Invalid ROUTES_MAP pair ignored: {pair}")
    logger.info(f"\u2705 Parsed ROUTES_MAP: {routes_map}")
    return routes_map

def load_routes_from_env() -> dict:
    return get_routes_map()

def save_routes_to_env(routes_map: dict):
    os.environ["ROUTES_MAP"] = ",".join(f"{k}:{v}" for k, v in routes_map.items())
    logger.info("\ud83d\udcdd Updated in-memory ROUTES_MAP (won’t persist to .env)")

def get_admin_ids() -> set[int]:
    raw = os.getenv("ADMIN_IDS", "")
    if not raw:
        logger.warning("\u26A0\uFE0F ADMIN_IDS environment variable is missing or empty.")
        return set()
    logger.warning(f"\u26A0\uFE0F ADMIN_IDS environment variable is loaded: {raw}")
    try:
        return set(int(x.strip()) for x in raw.split(",") if x.strip().isdigit())
    except ValueError:
        logger.error("\u274C Failed to parse ADMIN_IDS. Please check format.")
        return set()

# === AUDIO / IMAGE PROCESSING ===
def transcribe_audio_with_whisper(file_path: str) -> str:
    try:
        segments, _ = model.transcribe(file_path)
        return " ".join(segment.text for segment in segments if segment.text).strip()
    except Exception as e:
        logger.error(f"Whisper transcription failed: {e}")
        return ""

def extract_text_from_image(image_path):
    try:
        img = Image.open(image_path)
        return pytesseract.image_to_string(img).strip()
    except Exception as e:
        return f"OCR error: {str(e)}"

# === HOMEWORK DETECTION ===
def is_homework_like(message: str) -> bool:
    if not message:
        return False
    text = message.lower()
    spam_phrases = [
        "click here", "free gift", "bonus", "subscribe", "win", ".icu", ".xyz", "offer", "buy now", "cash prize"
    ]
    if any(phrase in text for phrase in spam_phrases):
        return False

    strong_keywords = [
        "homework", "hw", "assignment", "classwork", "task", "work", "worksheet", "project", "activity", "practice",
        "revision", "test prep", "reading", "notes", "prep", "quiz", "exam", "deadline", "submission", "due",
        "final", "presentation", "lab report", "writeup", "summary", "essay", "recap", "module", "draft", "slides",
        "questions", "maths", "science", "english", "dzongkha", "to-do", "school stuff", "pdf", "page no", "page",
        "write", "do this", "read", "solve", "finish", "study", "submit", "\U0001F4DD", "\U0001F4DA", "\u270D\uFE0F", "\u2705", "\U0001F4D6"
    ]
    weak_keywords = ["work", "read", "write", "draw", "solve", "fill", "copy", "prepare", "practice", "home task"]

    strong_hits = sum(1 for word in strong_keywords if word in text)
    weak_hits = sum(1 for word in weak_keywords if word in text)
    pattern_hits = sum(1 for h in ["page", "submit", "due", "q.", "ex.", "exercise", "copy this"] if h in text)

    return (strong_hits * 2 + weak_hits + pattern_hits) >= 3 or len(text) > 50

# === FORWARDING UTILITIES ===
def get_media_type_icon(message: Message) -> str:
    if message.photo:
        return "\U0001F5BC\uFE0F"
    elif message.document:
        return "\U0001F4C4"
    elif message.video:
        return "\U0001F39E\uFE0F"
    elif message.audio:
        return "\U0001F3B5"
    elif message.voice:
        return "\U0001F3A4"
    elif message.sticker:
        return "\U0001F516"
    elif message.text:
        return "\u270F\uFE0F"
    return "\U0001F4CE"

async def forward_message_to_parents(message, routes_map):
    source_chat_id = message.chat.id
    dest_ids = routes_map.get(str(source_chat_id))
    if not dest_ids:
        return
    for dest_id in dest_ids:
        try:
            await message.forward(chat_id=int(dest_id))
        except Exception as e:
            logger.error(f"Failed to forward message to {dest_id}: {e}")

def escape_markdown(text: str) -> str:
    escape_chars = r'\\_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)
