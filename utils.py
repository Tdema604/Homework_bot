import os
import tempfile
import subprocess
import json
from datetime import datetime, timedelta

import speech_recognition as sr
from pytesseract import image_to_string
from PIL import Image
from dotenv import set_key
from telegram import Message, Update
from telegram.ext import ContextTypes
from telegram.constants import ChatAction
from telegram.helpers import escape_markdown
from telegram.ext.filters import MessageFilter

# --- Admin Filter ---
class AdminFilter(MessageFilter):
    def filter(self, message: Message) -> bool:
        return str(message.from_user.id) in message.bot_data.get("ADMIN_CHAT_IDS", [])

admin_filter = AdminFilter()

def is_admin(user_id, bot_data):
    return str(user_id) in bot_data.get("ADMIN_CHAT_IDS", [])

# --- Junk Filter ---
def is_junk_message(message: Message):
    if not message.text:
        return False
    lowered = message.text.lower()
    return (
        "free vpn" in lowered
        or "/nayavpn" in lowered
        or "http://" in lowered
        or "https://" in lowered
        or "@" in lowered
    )

# --- Get Target Chat ---
def get_target_chat_id(source_chat_id: int, routes_map: dict) -> int | None:
    return routes_map.get(str(source_chat_id))

# --- OCR: Extract text from image ---
async def extract_text_from_image(file):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
            await file.download_to_drive(tmp_file.name)
            img = Image.open(tmp_file.name)
            text = image_to_string(img)
        os.remove(tmp_file.name)
        return text
    except Exception as e:
        print(f"OCR Error: {e}")
        return ""

# --- Audio Transcription using Whisper and fallback to Google ---
async def transcribe_audio_with_whisper(file):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as tmp_file:
            await file.download_to_drive(tmp_file.name)
            ogg_path = tmp_file.name

        wav_path = ogg_path.replace(".ogg", ".wav")
        subprocess.run(["ffmpeg", "-y", "-i", ogg_path, wav_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)

        try:
            text = recognizer.recognize_whisper(audio_data)
        except Exception:
            text = recognizer.recognize_google(audio_data)

        os.remove(ogg_path)
        os.remove(wav_path)
        return text
    except Exception as e:
        print(f"Whisper/Google STT Error: {e}")
        return ""

# --- Keyword Detection ---
def is_homework_text(text: str):
    keywords = ["homework", "classwork", "hw", "cw", "work", "assignment", "task", "project"]
    return any(kw in text.lower() for kw in keywords)

# --- Forward Homework Message ---
async def forward_homework(update: Update, context: ContextTypes.DEFAULT_TYPE, transcribed_text=None):
    message = update.message
    from_chat_id = str(message.chat_id)
    to_chat_id = get_target_chat_id(from_chat_id, context.bot_data)

    if not to_chat_id:
        return

    user = message.from_user
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    context.bot_data.setdefault("SENDER_LOGS", {})[str(user.id)] = {
        "name": user.full_name,
        "last_message": message.text or message.caption or "[Media]",
        "timestamp": now,
    }

    try:
        if transcribed_text:
            await context.bot.send_chat_action(chat_id=to_chat_id, action=ChatAction.TYPING)
            await context.bot.send_message(
                chat_id=to_chat_id,
                text=f"🎙️ *Voice/Audio Transcription:*\n{escape_markdown(transcribed_text)}",
                parse_mode="MarkdownV2",
            )
        else:
            if message.text:
                await context.bot.send_message(chat_id=to_chat_id, text=message.text)
            elif message.photo:
                await context.bot.send_photo(chat_id=to_chat_id, photo=message.photo[-1].file_id, caption=message.caption)
            elif message.document:
                await context.bot.send_document(chat_id=to_chat_id, document=message.document.file_id, caption=message.caption)
            elif message.voice:
                await context.bot.send_voice(chat_id=to_chat_id, voice=message.voice.file_id, caption=message.caption)
            elif message.audio:
                await context.bot.send_audio(chat_id=to_chat_id, audio=message.audio.file_id, caption=message.caption)
            elif message.video:
                await context.bot.send_video(chat_id=to_chat_id, video=message.video.file_id, caption=message.caption)
    except Exception as e:
        print(f"Error forwarding message: {e}")

# --- Weekly Summary ---
def get_weekly_summary(context, group_id=None):
    logs = context.bot_data.get("FORWARDED_LOGS", {})
    now = datetime.now()
    past_week = now - timedelta(days=7)
    summaries = []

    groups_to_check = [group_id] if group_id else logs.keys()

    for gid in groups_to_check:
        entries = logs.get(str(gid), [])
        recent = [e for e in entries if datetime.fromisoformat(e["timestamp"]) >= past_week]
        summaries.append(f"Group {gid}: {len(recent)} homework messages in the past 7 days.")

    return "\n".join(summaries) if summaries else "No logs found for the past 7 days."

def clear_homework_log(context):
    context.bot_data["FORWARDED_LOGS"] = {}

# --- Sender Activity Tracker ---
def track_sender_activity(bot_data: dict, user, message_text: str):
    if "SENDER_ACTIVITY" not in bot_data:
        bot_data["SENDER_ACTIVITY"] = {}

    sender_id = str(user.id)
    bot_data["SENDER_ACTIVITY"][sender_id] = {
        "name": user.full_name,
        "last_message": message_text[:100],
        "timestamp": datetime.now().isoformat(),
    }

def list_sender_activity(context):
    log = context.bot_data.get("SENDER_ACTIVITY", {})
    if not log:
        return "No recent sender activity found."
    lines = []
    for user_id, entry in log.items():
        name = entry["name"]
        msg = entry["last_message"]
        ts = entry["timestamp"]
        lines.append(f"{name} (ID: {user_id})\n🕒 {ts}\n💬 {msg}\n")
    return "\n".join(lines)

def clear_sender_data(context):
    context.bot_data["SENDER_ACTIVITY"] = {}

# --- Route Parsing and ENV Sync ---
def parse_routes_map(raw_map: str) -> dict:
    routes = {}
    for route in raw_map.split(","):
        if ":" in route:
            src, dst = route.strip().split(":")
            routes[src.strip()] = dst.strip()
    return routes

def add_route_to_env(student_id: int, parent_id: int, env_path=".env"):
    env_routes = os.getenv("ROUTES_MAP", "")
    routes = parse_routes_map(env_routes)
    routes[str(student_id)] = str(parent_id)
    new_routes = ",".join([f"{k}:{v}" for k, v in routes.items()])
    set_key(env_path, "ROUTES_MAP", new_routes)
    return routes

def delete_route_from_env(student_id: int, env_path=".env"):
    env_routes = os.getenv("ROUTES_MAP", "")
    routes = parse_routes_map(env_routes)
    if str(student_id) in routes:
        del routes[str(student_id)]
        new_routes = ",".join([f"{k}:{v}" for k, v in routes.items()])
        set_key(env_path, "ROUTES_MAP", new_routes)
    return routes
