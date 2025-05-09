import logging
import os
import html
import tempfile
import subprocess
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from pydub import AudioSegment
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from telegram.ext import (CommandHandler, MessageHandler, filters, ContextTypes)
from utils import (
    escape_markdown, forward_message_to_parents, get_target_group_id,
    get_media_type_icon, is_homework_like, load_routes_from_env,
    get_routes_map, transcribe_audio_with_whisper
)
from decorators import admin_only
import pytesseract


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BT_TZ = ZoneInfo("Asia/Thimphu")
ROUTES = load_routes_from_env()

# === Bot Setup ===
def setup_bot_handlers(app):
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


# === Greetings ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now(BT_TZ)
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


# === Status ===
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now(BT_TZ).strftime('%Y-%m-%d %H:%M:%S')
    route_count = len(ROUTES)
    await update.message.reply_text(
        f"\u2705 Bot is online!\n\n\u23f0 Time: {now}\n\ud83e\udded Mapped groups: {route_count}"
    )


# === Help ===
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Use /status to check bot health or /id to see your current chat ID.", parse_mode=ParseMode.MARKDOWN)


# === Chat ID ===
async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user
    await update.message.reply_text(
        f"Chat ID: `{chat.id}`\nUser ID: `{user.id}`",
        parse_mode=ParseMode.MARKDOWN
    )
    await update.message.reply_text(
       f"👥 *Chat Info*\n"
       f"ID: `{chat.id}`\n"
       f"Title: `{chat.title or user.full_name}`\n"
       f"User ID: `{user.id}`",
       parse_mode=ParseMode.MARKDOWN
)

# === Sender Activity ===
async def list_senders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    activity = context.bot_data.get("SENDER_ACTIVITY", {})
    if not activity:
        await update.message.reply_text("📭 No sender activity recorded.")
        return
    lines = [
        f"<b>{html.escape(data['name'])}</b> ({user_id})\n🕒 {data['timestamp']}\n📩 {html.escape(data['last_message'])}"
        for user_id, data in activity.items()
    ]
    await update.message.reply_text("🧾 <b>Recent Sender Activity</b>\n\n" + "\n\n".join(lines), parse_mode=ParseMode.HTML)


async def clear_senders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.bot_data["SENDER_ACTIVITY"] = {}
    await update.message.reply_text("🧹 Sender log cleared!", parse_mode=ParseMode.HTML)


# === Forwarding Logic ===
def is_homework_text(text: str) -> bool:
    if not text:
        return False
    text = text.lower()
    spam_patterns = [r"@.*bot", r"http[s]?://", r"join.*channel", r"vpn", r"shop", r"offer", r"sale", r"discount"]
    if any(re.search(pat, text) for pat in spam_patterns):
        return False
    keywords = ["homework", "assignment", "math", "english", "due", "page", "write", "chapter", "science", "question"]
    return any(word in text for word in keywords)


async def forward_homework_if_valid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    source_chat_id = update.effective_chat.id
    routes_map = context.bot_data.get("ROUTES_MAP", {})
    dest_ids = routes_map.get(str(source_chat_id))
    if not dest_ids:
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
                extracted_text = transcribe_audio_with_whisper(tf.name)

        elif message.video:
            video_file = await message.video.get_file()
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as video_temp:
                await video_file.download_to_drive(video_temp.name)

            audio_path = video_temp.name + ".mp3"
            subprocess.run(["ffmpeg", "-i", video_temp.name, "-q:a", "0", "-map", "a", audio_path, "-y"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            extracted_text = transcribe_audio_with_whisper(audio_path)

            os.remove(video_temp.name)
            os.remove(audio_path)

        if not is_homework_text(extracted_text):
            return

        for dest_id in dest_ids:
            try:
                await message.forward(chat_id=int(dest_id))
            except Exception as e:
                logger.error(f"Failed to forward to {dest_id}: {e}")

    except Exception as e:
        logger.exception("Error in forward_homework_if_valid")
