import os
import tempfile
import subprocess
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

import speech_recognition as sr
from pytesseract import image_to_string
from PIL import Image
from dotenv import set_key
from telegram import Message, Update
from telegram.ext import ContextTypes
from telegram.constants import ChatAction
from telegram.helpers import escape_markdown
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
# --- Setup --- #
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Admin Verification --- #
def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if user is admin"""
    return str(update.effective_user.id) in map(str, context.bot_data.get("ADMIN_CHAT_IDS", []))

# --- Message Filtering --- #
def is_junk_message(message: Message) -> bool:
    """Detect spam messages"""
    if not message.text:
        return False
    text = message.text.lower()
    spam_indicators = [
        "http://", "https://", "@", "#",
        "free vpn", "nayavpn", "join", "click"
    ]
    return any(indicator in text for indicator in spam_indicators)

def is_homework_text(text: str) -> bool:
    """Detect homework-related content"""
    if not text:
        return False
    keywords = [
        "hw", "homework", "assignment",
        "due", "submit", "task", "project"
    ]
    return any(kw in text.lower() for kw in keywords)

# --- Media Processing --- #
async def extract_text_from_image(image_path: str) -> str:
    """Extract text from images using OCR"""
    try:
        img = Image.open(image_path)
        text = image_to_string(img)
        return text.strip() if text else ""
    except Exception as e:
        logger.error(f"OCR failed: {e}")
        return ""

async def transcribe_audio(audio_path: str) -> str:
    """Transcribe audio using Whisper (fallback to Google)"""
    try:
        recognizer = sr.Recognizer()
        with sr.AudioFile(audio_path) as source:
            audio = recognizer.record(source)
        
        try:
            return recognizer.recognize_whisper(audio)
        except Exception:
            return recognizer.recognize_google(audio)
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        return ""

# --- Core Forwarding Logic --- #
async def forward_homework(
    context: ContextTypes.DEFAULT_TYPE,
    message: Message,
    routes_map: Dict[int, int]
) -> bool:
    """
    Forward messages to parent group with:
    - Text/photo support
    - OCR for images
    - Audio transcription
    - Error handling
    """
    try:
        target_chat = routes_map.get(message.chat_id)
        if not target_chat:
            return False

        # Notify typing action
        await context.bot.send_chat_action(
            chat_id=target_chat,
            action=ChatAction.TYPING
        )

        # Handle different message types
        if message.text:
            await context.bot.send_message(
                chat_id=target_chat,
                text=f"📝 Homework Alert!\n\n{message.text}"
            )
            return True

        elif message.photo:
            # Download and process image
            with tempfile.NamedTemporaryFile(suffix=".jpg") as tmp:
                photo = await message.photo[-1].get_file()
                await photo.download_to_drive(tmp.name)
                ocr_text = await extract_text_from_image(tmp.name)

            if ocr_text:
                await context.bot.send_message(
                    chat_id=target_chat,
                    text=f"📸 Image Text:\n\n{ocr_text}"
                )
            await context.bot.send_photo(
                chat_id=target_chat,
                photo=message.photo[-1].file_id,
                caption=message.caption
            )
            return True

        elif message.voice or message.audio:
            # Download and transcribe audio
            with tempfile.NamedTemporaryFile(suffix=".ogg") as tmp:
                audio = await (message.voice or message.audio).get_file()
                await audio.download_to_drive(tmp.name)
                transcript = await transcribe_audio(tmp.name)

            if transcript:
                await context.bot.send_message(
                    chat_id=target_chat,
                    text=f"🎙️ Audio Transcript:\n\n{transcript}"
                )
            await context.bot.send_voice(
                chat_id=target_chat,
                voice=message.voice.file_id if message.voice else None,
                audio=message.audio.file_id if message.audio else None
            )
            return True

        return False

    except Exception as e:
        logger.error(f"Forwarding failed: {e}")
        return False

# --- Route Management --- #
def parse_routes_map(raw_routes: str) -> Dict[int, int]:
    """Parse ROUTES_MAP from .env string"""
    routes = {}
    if not raw_routes:
        return routes
    
    for route in raw_routes.split(","):
        try:
            src, dst = map(int, route.strip().split(":"))
            routes[src] = dst
        except (ValueError, AttributeError):
            continue
    return routes

def sync_routes_to_env(routes: Dict[int, int], env_path=".env") -> None:
    """Update .env file with current routes"""
    route_str = ",".join(f"{k}:{v}" for k, v in routes.items())
    set_key(env_path, "ROUTES_MAP", route_str)

# --- Activity Tracking --- #
def track_sender_activity(context: ContextTypes.DEFAULT_TYPE, update: Update) -> None:
    """Log sender activity in bot_data"""
    user = update.effective_user
    context.bot_data.setdefault("SENDER_ACTIVITY", {})[str(user.id)] = {
        "name": user.full_name,
        "last_message": update.message.text or "[media]",
        "timestamp": datetime.now().isoformat()
    }

def get_activity_summary(context: ContextTypes.DEFAULT_TYPE) -> str:
    """Generate formatted activity log"""
    activities = context.bot_data.get("SENDER_ACTIVITY", {})
    if not activities:
        return "No activity yet"
    
    return "\n".join(
        f"{data['name']}: {data['last_message'][:50]}..."
        for _, data in activities.items()
)
