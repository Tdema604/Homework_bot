import logging
import os
import time
import html
import io
import speech_recognition as sr
import aiofiles
import subprocess
import uuid
import tempfile
import re
import pytz
import speech_recognition as sr
from datetime import datetime, timedelta
from pydub import AudioSegment
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from telegram.constants import ChatAction
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from telegram.ext import CommandHandler, MessageHandler, filters
from utils import (
    escape_markdown,forward_message_to_parents, get_target_group_id,
    get_media_type_icon,
    is_homework_like,
    load_routes_from_env,
    save_routes_to_env,
    get_routes_map,get_forward_target,transcribe_audio_with_whisper 
)
from PIL import Image
from decorators import admin_only  # Ensure this exists

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

BT_TZ = pytz.timezone("Asia/Thimphu")
ROUTES = load_routes_from_env()

# Initialize recognizer
recognizer = sr.Recognizer()

# Use an audio file (replace with your actual file path)
audio_file_path = "path_to_your_audio_file.wav"

# Load the audio file
with sr.AudioFile(audio_file_path) as source:
    audio = recognizer.record(source)

# Recognize speech using Google Web Speech API (requires internet)
try:
    print("Transcription: " + recognizer.recognize_google(audio))
except sr.UnknownValueError:
    print("Sorry, could not understand the audio.")
except sr.RequestError as e:
    print("Could not request results; check your network connection.")


def setup_bot_handlers(app):
    # Admin + general commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("id", id_command))
    app.add_handler(CommandHandler("reload_config", reload_config))
    app.add_handler(CommandHandler("weekly_summary", weekly_summary))
    app.add_handler(CommandHandler("clear_homework_log", clear_homework_log))
    app.add_handler(CommandHandler("list_senders", list_senders))
    app.add_handler(CommandHandler("clear_senders", clear_senders))
    app.add_handler(CommandHandler("list_routes", list_routes))
    app.add_handler(CommandHandler("add_routes", add_routes))
    app.add_handler(CommandHandler("remove_routes", remove_routes))
    app.add_handler(CommandHandler("ocr_debug", ocr_debug))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, forward_homework_if_valid))
    app.add_handler(MessageHandler(filters.VOICE, handle_audio))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.datetime.now(BT_TZ)
    hour = now.hour
    weekday = now.strftime("%A")

    if hour < 12:
        time_emoji = "☀️"
        greeting = "Good morning"
    elif hour < 17:
        time_emoji = "🌤️"
        greeting = "Good afternoon"
    elif hour < 21:
        time_emoji = "🌙"
        greeting = "Good evening"
    else:
        time_emoji = "🌌"
        greeting = "Good night"

    weekday_emoji = {
        "Monday": "✨",
        "Friday": "🎉",
        "Saturday": "😎",
        "Sunday": "🧘‍♀️",
    }.get(weekday, "📚")

    await update.message.reply_text(f"{time_emoji} {greeting}, teacher!\n\nI'm the Homework Forwarder Bot. {weekday_emoji}")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.datetime.now(BT_TZ).strftime('%Y-%m-%d %H:%M:%S')
    route_count = len(ROUTES)
    await update.message.reply_text(
        f"\u2705 Bot is online!\n\n\u23f0 Time: {now}\n\ud83e\udded Mapped groups: {route_count}"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_admin(update.effective_user):
        await update.message.reply_text("""
        ❓ *Admin Commands:*
        /start - Bot greeting
        /status - Bot status
        /help - Show this help
        /reload_config - Reload routing
        /weekly_summary - Last 7 days of logs
        /clear_homework_log - Clear logs
        /list_senders - List active teachers
        /clear_senders - Reset sender log
        /id - Show current chat ID
        """, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("""
        👋 *Available Commands:*
        /start - Say hi to bot
        /help - Show available commands
        /id - Get your current group/user ID
        """, parse_mode=ParseMode.MARKDOWN)

chat_id = None  # Initial default

async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global chat_id  # Reference the global variable
    chat = update.effective_chat
    user = update.effective_user
    chat_id = chat.id  # Store the current chat ID globally

    await update.message.reply_text(
        f"Chat ID: `{chat.id}`\nUser ID: `{user.id}`",
        parse_mode=ParseMode.MARKDOWN
    )


async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Your logic to forward the message
    message = update.message
    target_chat_id = 123456789  # Replace with your actual target chat ID
    await context.bot.forward_message(
        chat_id=target_chat_id,
        from_chat_id=message.chat.id,
        message_id=message.message_id
    )

# === Sender Activity Utilities ===
async def list_senders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    activity = context.bot_data.get("SENDER_ACTIVITY", {})
    if not activity:
        await update.message.reply_text("📭 No sender activity recorded.")
        return
    lines = []
    for user_id, data in activity.items():
        lines.append(f"<b>{html.escape(data['name'])}</b> ({user_id})\n🕒 {data['timestamp']}\n📩 {html.escape(data['last_message'])}")
    await update.message.reply_text("🧾 <b>Recent Sender Activity</b>\n\n" + "\n\n".join(lines), parse_mode=ParseMode.HTML)

async def clear_senders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.bot_data["SENDER_ACTIVITY"] = {}
    await update.message.reply_text("🧹 Sender log cleared!", parse_mode=ParseMode.HTML)


# === Homework forwarder ===
# Function to handle voice messages

def convert_to_wav(input_file, output_file):
    """Convert any audio file to .wav format"""
    audio = AudioSegment.from_file(input_file)
    audio.export(output_file, format="wav")

def process_audio(update: Update, context: CallbackContext):
    audio_file = update.message.voice.get_file()
    audio_file_path = 'path_to_save_audio/voice_message.ogg'  # Path to store the downloaded audio file
    
    # Download the audio file from Telegram
    audio_file.download(audio_file_path)
        print(f"Audio file path: {audio_file_path}")

    # Convert .ogg to .wav using pydub if needed
    from pydub import AudioSegment
    sound = AudioSegment.from_ogg(audio_file_path)
    wav_path = 'path_to_save_audio/voice_message.wav'
    sound.export(wav_path, format="wav")

    # Use the SpeechRecognition library to process the .wav file
    with sr.AudioFile(wav_path) as source:
        recognizer = sr.Recognizer()
        audio = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio)
            print(f"Recognized text: {text}")
        except sr.UnknownValueError:
            print("Google Speech Recognition could not understand audio.")
        except sr.RequestError as e:
            print(f"Could not request results from Google Speech Recognition service; {e}")

async def handle_audio(update: Update, context):
    """Handle incoming audio messages and convert to text"""
    if update.message.voice:
        # Get the file ID and download the audio
        file = await update.message.voice.get_file()
        file.download('received_audio.ogg')

        # Convert the .ogg file to .wav
        convert_to_wav('received_audio.ogg', 'converted_audio.wav')

        # Process the audio file to transcribe
        transcription = process_audio_file('converted_audio.wav')

        if transcription:
            await update.message.reply_text(f"Transcribed homework: {transcription}")
        else:
            await update.message.reply_text("Sorry, I couldn't transcribe the audio.")


def is_homework_text(text: str) -> bool:
    if not text:
        return False

    # Normalize
    text = text.lower()

    # Obvious spam indicators
    spam_patterns = [
        r"@.*bot", r"http[s]?://", r"join.*channel", r"vpn", r"shop", r"offer", r"sale", r"discount"
    ]
    if any(re.search(pat, text) for pat in spam_patterns):
        return False

    # Academic keywords
    keywords = ["homework", "assignment", "math", "english", "due", "page", "write", "chapter", "science", "question"]
    return any(word in text for word in keywords)

async def forward_homework_if_valid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    source_chat_id = update.effective_chat.id
    bot = context.bot
    
    # Access the routes_map from bot_data
    routes_map = context.bot_data.get("ROUTES_MAP", {})
    print(f"📥 Received message from {source_chat_id}: {message.text or '[non-text content]'}")
    print(f"Loaded routes_map: {routes_map}")  # Debug log to check routes map

    dest_ids = routes_map.get(str(source_chat_id))
    if not dest_ids:
        print(f"No destination IDs found for source_chat_id: {source_chat_id}")
        return

    extracted_text = ""

    try:
        if message.text:
            extracted_text = message.text

        elif message.photo:
            photo = message.photo[-1]
            with tempfile.NamedTemporaryFile(suffix=".jpg") as tf:
                await photo.get_file().download_to_drive(tf.name)
                extracted_text = pytesseract.image_to_string(tf.name)

        elif message.voice or message.audio:
            media = message.voice or message.audio
            suffix = ".ogg" if message.voice else ".mp3"
            with tempfile.NamedTemporaryFile(suffix=suffix) as tf:
                await media.get_file().download_to_drive(tf.name)
                extracted_text = transcribe_audio(tf.name)

        elif message.video:
            video_file = await message.video.get_file()
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as video_temp:
                await video_file.download_to_drive(video_temp.name)

            # Extract audio using ffmpeg
            audio_path = video_temp.name + ".mp3"
            command = ["ffmpeg", "-i", video_temp.name, "-q:a", "0", "-map", "a", audio_path, "-y"]
            subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # Transcribe audio
            extracted_text = transcribe_audio(audio_path)

            # Clean up
            os.remove(video_temp.name)
            os.remove(audio_path)

        else:
            return

        # If extracted text doesn't meet the homework condition, do nothing
        if not is_homework_text(extracted_text):
            return

        # Forward the message to all the destination IDs
        for dest_id in dest_ids:
            try:
                await message.forward(chat_id=int(dest_id))
                print(f"Message forwarded to {dest_id}")
            except Exception as e:
                print(f"Failed to forward to {dest_id}: {e}")

    except Exception as e:
        print(f"[ERROR] Failed to process message: {e}")
        print("✅ forward_homework_if_valid() called")

# === Admin Utilities ===
async def ocr_debug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        photo_file = await update.message.photo[-1].get_file()
        image_bytes = await photo_file.download_as_bytearray()
        image = Image.open(io.BytesIO(image_bytes))

        extracted_text = pytesseract.image_to_string(image)
        await update.message.reply_text(f"🧠 OCR Debug:\n<pre>{html.escape(extracted_text)}</pre>", parse_mode=ParseMode.HTML)

async def reload_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    load_dotenv()
    context.bot_data["ROUTES_MAP"] = get_routes_map()
    await update.message.reply_text("♻️ Configuration reloaded from .env!", parse_mode=ParseMode.HTML)

async def list_routes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    routes = context.bot_data.get("ROUTES_MAP", {})
    if not routes:
        await update.message.reply_text("🚫 No active routes found.")
        return
    formatted = "\n".join([f"<code>{k}</code> ➜ <code>{v}</code>" for k, v in routes.items()])
    await update.message.reply_text(f"📍 <b>Active Routes</b>\n{formatted}", parse_mode=ParseMode.HTML)

async def add_routes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        src, dest = int(context.args[0]), int(context.args[1])
        routes = context.bot_data.setdefault("ROUTES_MAP", {})
        routes[src] = dest
        save_routes_to_env(routes)
        await update.message.reply_text(f"✅ Route added: <code>{src}</code> ➜ <code>{dest}</code>", parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.exception(e)
        await update.message.reply_text("⚠️ Usage: /add_routes [source_chat_id] [destination_chat_id]")

async def remove_routes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        src = int(context.args[0])
        routes = context.bot_data.setdefault("ROUTES_MAP", {})
        if src in routes:
            del routes[src]
            save_routes_to_env(routes)
            await update.message.reply_text(f"❌ Route removed for source: <code>{src}</code>", parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text("❗ Source chat ID not found in routes.")
    except Exception as e:
        logger.exception(e)
        await update.message.reply_text("⚠️ Usage: /remove_routes [source_chat_id]")

# === Homework Log Utilities ===
async def weekly_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logs = context.bot_data.get("FORWARDED_LOGS", [])
    one_week_ago = time.time() - 7 * 86400
    summary = [log for log in logs if log["timestamp"] >= one_week_ago]
    
    if not summary:
        await update.message.reply_text("📭 No homework forwarded in the past 7 days.")
        return

    formatted = "\n".join(
        f"{log['type']} <b>{log['sender']}</b>: {html.escape(log['content'])}" for log in summary[-20:]
    )
    await update.message.reply_text(
        f"🗓️ <b>Last 7 Days Summary</b>\n\n{formatted}", parse_mode=ParseMode.HTML
    )

async def clear_homework_log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.bot_data["FORWARDED_LOGS"] = []
    await update.message.reply_text("🧹 Homework log cleared!", parse_mode=ParseMode.HTML)

# === Sender Activity Utilities ===
async def list_senders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    activity = context.bot_data.get("SENDER_ACTIVITY", {})
    if not activity:
        await update.message.reply_text("📭 No sender activity recorded.")
        return
    lines = []
    for user_id, data in activity.items():
        lines.append(f"<b>{html.escape(data['name'])}</b> ({user_id})\n🕒 {data['timestamp']}\n📩 {html.escape(data['last_message'])}")
    await update.message.reply_text("🧾 <b>Recent Sender Activity</b>\n\n" + "\n\n".join(lines), parse_mode=ParseMode.HTML)

async def clear_senders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.bot_data["SENDER_ACTIVITY"] = {}
    await update.message.reply_text("🧹 Sender log cleared!", parse_mode=ParseMode.HTML)