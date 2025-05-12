import os
import tempfile
import logging
import platform  # For OS detection
import subprocess
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
import speech_recognition as sr
import pytesseract
from pytesseract import image_to_string
from PIL import Image
from dotenv import set_key
from datetime import datetime, timedelta
from typing import Dict, Optional
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

# --- Tesseract Configuration --- #
if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    TESSDATA_PREFIX = r'C:\Program Files\Tesseract-OCR\tessdata'

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

# --- get_target_chat_id --- #
def get_target_chat_id(src_chat_id: int, routes_map: Dict[int, int]) -> Optional[int]:
    """Get the target chat ID from the routes map using the source chat ID."""
    return routes_map.get(src_chat_id)

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
def setup_dzongkha_ocr():
    """Ensure Dzongkha language support exists (Linux only)"""
    if platform.system() != "Windows":
        dzo_path = f"{TESSDATA_PREFIX}/dzo.traineddata"
        if not os.path.exists(dzo_path):
            os.makedirs(TESSDATA_PREFIX, exist_ok=True)
            os.system(f"curl -L 'https://github.com/tesseract-ocr/tessdata/raw/main/dzo.traineddata' -o '{dzo_path}'")

async def extract_text_from_image(image_path: str) -> str:
    """Extract text from images with Dzongkha support"""
    try:
        setup_dzongkha_ocr()
        img = Image.open(image_path)
        lang = 'dzo+eng' if platform.system() != "Windows" else 'eng'
        text = image_to_string(img, lang=lang)
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
def add_route_to_env(student_id: str, parent_id: str) -> str:
    """Add a new route to ROUTES_MAP in the .env file (manual for now)."""
    try:
        routes_map = os.getenv("ROUTES_MAP", "")
        route_dict = dict(pair.split(":") for pair in routes_map.split(",") if pair)

        if student_id in route_dict:
            return f"❌ Route already exists for student group {student_id}."

        route_dict[student_id] = parent_id
        updated_routes = ",".join(f"{k}:{v}" for k, v in route_dict.items())

        # Simulate saving to .env (this should ideally be manual in production)
        with open(".env", "r") as file:
            lines = file.readlines()

        with open(".env", "w") as file:
            for line in lines:
                if line.startswith("ROUTES_MAP="):
                    file.write(f"ROUTES_MAP={updated_routes}\n")
                else:
                    file.write(line)

        return f"✅ Added route: {student_id} ➡️ {parent_id}"

    except Exception as e:
        return f"⚠️ Failed to add route: {e}"

def delete_route_from_env(student_id: str) -> str:
    """Delete a route from ROUTES_MAP in the .env file."""
    try:
        routes_map = os.getenv("ROUTES_MAP", "")
        route_dict = dict(pair.split(":") for pair in routes_map.split(",") if pair)

        if student_id not in route_dict:
            return f"❌ No route found for student group {student_id}."

        del route_dict[student_id]
        updated_routes = ",".join(f"{k}:{v}" for k, v in route_dict.items())

        # Simulate saving to .env (ideally should be manual in production)
        with open(".env", "r") as file:
            lines = file.readlines()

        with open(".env", "w") as file:
            for line in lines:
                if line.startswith("ROUTES_MAP="):
                    file.write(f"ROUTES_MAP={updated_routes}\n")
                else:
                    file.write(line)

        return f"🗑️ Deleted route for student group {student_id}."

    except Exception as e:
        return f"⚠️ Failed to delete route: {e}"


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
def list_sender_activity(bot_data):
    """List the sender activity based on the recorded sender data."""
    sender_activity = bot_data.get("SENDER_ACTIVITY", {})
    
    # Sort the senders based on timestamp of their last message (descending)
    sorted_senders = sorted(sender_activity.items(), key=lambda item: item[1]['timestamp'], reverse=True)
    
    # Format the activity into a readable string
    activity_list = []
    for sender_id, activity in sorted_senders:
        name = activity.get("name", "Unknown Sender")
        last_message = activity.get("last_message", "No messages")
        timestamp = activity.get("timestamp", "No timestamp")
        activity_list.append(f"Sender ID: {sender_id}, Name: {name}, Last Message: {last_message}, Timestamp: {timestamp}")
    
    return "\n".join(activity_list) if activity_list else "No sender activity recorded."

def clear_sender_data(context: ContextTypes.DEFAULT_TYPE) -> str:
    """Clear the sender activity log."""
    context.application.bot_data["SENDER_ACTIVITY"] = {}
    return "Sender activity data has been cleared."


def track_sender_activity(context: ContextTypes.DEFAULT_TYPE, update: Update) -> None:
    """Log sender activity in bot_data"""
    user = update.effective_user
    context.bot_data.setdefault("SENDER_ACTIVITY", {})[str(user.id)] = {
        "name": user.full_name,
        "last_message": update.message.text or "[media]",
        "timestamp": datetime.now().isoformat()
    }

def get_weekly_summary(bot_data):
    """Get the weekly homework summary for the past 7 days."""
    # Get the current time and the time for 7 days ago
    now = datetime.now()
    start_of_week = now - timedelta(days=7)  # 7 days ago
    
    # Filter logs from the past 7 days
    weekly_summary = []
    for log in bot_data.get("FORWARDED_LOGS", []):
        # Ensure that the log contains a timestamp and that it's within the past 7 days
        if "timestamp" in log:
            timestamp = datetime.fromtimestamp(log["timestamp"])
            if timestamp >= start_of_week:
                weekly_summary.append(log)
    
    return weekly_summary

# Function to clear homework logs
def clear_homework_log(bot_data):
    """Clear all homework logs from the past week."""
    bot_data["FORWARDED_LOGS"] = []

def get_activity_summary(context: ContextTypes.DEFAULT_TYPE) -> str:
    """Generate formatted activity log"""
    activities = context.bot_data.get("SENDER_ACTIVITY", {})
    if not activities:
        return "No activity yet"
    
    return "\n".join(
        f"{data['name']}: {data['last_message'][:50]}..."
        for _, data in activities.items()
)
