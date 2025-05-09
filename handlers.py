import logging
import os
import html
import tempfile
import subprocess
import re
import pytesseract
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
from pydub import AudioSegment
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from telegram.ext import (Application, CommandHandler, MessageHandler, filters, ContextTypes)
from utils import (
    escape_markdown, forward_message_to_parents, get_target_group_id,
    get_media_type_icon, is_homework_like, load_routes_from_env,
    get_routes_map, transcribe_audio_with_whisper
)
from decorators import admin_only

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BT_TZ = ZoneInfo("Asia/Thimphu")
ROUTES = load_routes_from_env()
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# === Bot Setup ===
def setup_bot_handlers(app: Application) -> None:
    # Admin & General Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("id", id_command))

    # Admin Tools
    app.add_handler(CommandHandler("get_routes_map", get_routes_map))
    app.add_handler(CommandHandler("reload_config", reload_config))
    app.add_handler(CommandHandler("weekly_summary", weekly_summary))
    app.add_handler(CommandHandler("clear_homework_log", clear_homework_log))
    app.add_handler(CommandHandler("list_senders", list_senders))
    app.add_handler(CommandHandler("clear_senders", clear_senders))
    app.add_handler(CommandHandler("list_routes", list_routes))
    app.add_handler(CommandHandler("add_routes", add_routes))
    app.add_handler(CommandHandler("remove_routes", remove_routes))
    app.add_handler(CommandHandler("ocr_debug", ocr_debug))

    # Catch-all non-command messages (text, media, etc.)
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, forward_homework_if_valid))

# Only export what's needed
__all__ = ["setup_bot_handlers"]

logging.info("✅ Handlers successfully registered.")

# === Greetings ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"📥 /start from {user.username or user.id}")
    now = datetime.now(BT_TZ)
    hour = now.hour
    weekday = now.strftime("%A")

    if 5 <= hour < 12:
        return "Good morning! ☀️"
    elif 12 <= hour < 17:
        return "Good afternoon! 🌤️"
    elif 17 <= hour < 20:
        return "Good evening! 🌙"
    else:
        return "Good night! 🌌"

    weekday_emoji = {
        "Monday": "✨",
        "Friday": "🎉",
        "Saturday": "😎",
        "Sunday": "🧘‍♀️",
    }.get(weekday, "📚")
    
    await update.message.reply_text(f"{time_emoji} {greeting}, Teachers & Students!\n\nI'm the Homework Forwarder Bot. {weekday_emoji}")

# === Status ===
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now(BT_TZ).strftime('%Y-%m-%d %H:%M:%S')
    route_count = len(ROUTES)
    await update.message.reply_text(
        f"\u2705 Bot is online!\n\n\u23f0 Time: {now}\n\ud83e\udded Mapped groups: {route_count}"
    )


# === Help ===
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Use /status to check bot health or /id to see your current chat ID.", 
    parse_mode=ParseMode.MARKDOWN)

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

__all__ = ["id_command"]


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
    await update.message.reply_text("🧹 Sender activity log cleared!", parse_mode=ParseMode.HTML)

# === Route Map ===
async def list_routes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    routes_map = context.bot_data.get("ROUTES_MAP", {})
    if not routes_map:
        await update.message.reply_text("📭 No routes configured.")
        return

    route_list = "\n".join([f"Source: {source} -> Destinations: {', '.join(map(str, destinations))}" 
                           for source, destinations in routes_map.items()])
    await update.message.reply_text("🧭 <b>Configured Routes</b>\n\n" + route_list, parse_mode=ParseMode.HTML)

async def add_routes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("⚠️ Usage: /add_routes <source_chat_id> <dest_chat_id_1> <dest_chat_id_2> ...")
        return
    
    source_chat_id = context.args[0]
    destination_chat_ids = context.args[1:]

    routes_map = context.bot_data.get("ROUTES_MAP", {})
    routes_map[source_chat_id] = destination_chat_ids

    context.bot_data["ROUTES_MAP"] = routes_map
    await update.message.reply_text(f"✅ Routes added: Source {source_chat_id} -> Destinations: {', '.join(destination_chat_ids)}")

async def remove_routes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text("⚠️ Usage: /remove_routes <source_chat_id>")
        return
    
    source_chat_id = context.args[0]

    routes_map = context.bot_data.get("ROUTES_MAP", {})
    if source_chat_id in routes_map:
        del routes_map[source_chat_id]
        context.bot_data["ROUTES_MAP"] = routes_map
        await update.message.reply_text(f"✅ Route removed: Source {source_chat_id}")
    else:
        await update.message.reply_text(f"⚠️ No route found for Source {source_chat_id}")


# === Forwarding Logic ===
def is_homework_text(text: str):
    keywords = ["homework", "assignment", "worksheet", "submit",
        "classwork", "question", "due", "test", "exam",
        "page", "chapter", "topic", "notes", "activity"]
    return any(keyword in text.lower() for keyword in keywords)

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

        # Check for junk text
        if is_junk_text(extracted_text):
            logger.debug("Message identified as junk. Skipping.")
            return  # Skipping junk messages

        # If it's not junk and it is homework
        if not is_homework_text(extracted_text):
            return

        # Forward to parent groups if valid homework message
        for dest_id in dest_ids:
            try:
                await message.forward(chat_id=int(dest_id))
            except Exception as e:
                logger.error(f"Failed to forward to {dest_id}: {e}")

    except Exception as e:
        logger.exception("Error in forward_homework_if_valid")




async def clear_homework_log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.bot_data["FORWARDED_LOGS"] = []  # Clear the list of forwarded homework logs
    await update.message.reply_text("🧹 Homework log has been cleared successfully!", parse_mode=ParseMode.HTML)


# Optional: Reload logic to refresh routes from .env
def get_routes_map():
    routes_env = os.getenv("ROUTES_MAP", "").strip()
    if not routes_env:
        return {}

    try:
        return {
            str(source): [int(dest) for dest in destinations.split(",")]
            for source, destinations in (item.split(":") for item in routes_env.split(","))
        }
    except ValueError as e:
        logging.error(f"Failed to parse ROUTES_MAP: {e}")
        return {}

# 🛠️ Handler for /reload_config
async def reload_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in context.bot_data.get("ADMIN_CHAT_IDS", []):
        await update.message.reply_text("⛔ You’re not authorized to reload the config.")
        return

    routes_map = get_routes_map()
    context.bot_data["ROUTES_MAP"] = routes_map
    await update.message.reply_text(f"✅ Config reloaded. Total routes: {len(routes_map)}")

# Get the start and end of the past week
def get_week_range():
    today = datetime.today()
    start_of_week = today - timedelta(days=today.weekday())  # Get last Monday
    end_of_week = start_of_week + timedelta(days=6)  # Get last Sunday
    return start_of_week, end_of_week

# Generate a summary of forwarded homework messages for the last week
async def weekly_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Get the range of the last week
    start_of_week, end_of_week = get_week_range()

    # Access the logs or forwarded homework data (you may have to adjust this)
    forwarded_logs = context.bot_data.get("FORWARDED_LOGS", {})

    # Filter logs to get only those from the last week
    weekly_logs = [
        log for log in forwarded_logs.values()
        if start_of_week <= datetime.fromtimestamp(log['timestamp']) <= end_of_week
    ]

    if not weekly_logs:
        await update.message.reply_text("📭 No homework messages forwarded this week.", parse_mode=ParseMode.MARKDOWN)
        return

    # Aggregate data
    num_messages = len(weekly_logs)
    num_senders = len(set(log['sender_id'] for log in weekly_logs))
    
    # Optionally, you can format the results nicely
    summary = f"📅 Weekly Homework Summary ({start_of_week.strftime('%Y-%m-%d')} to {end_of_week.strftime('%Y-%m-%d')})\n\n"
    summary += f"🔢 Total Messages Forwarded: {num_messages}\n"
    summary += f"👤 Unique Senders: {num_senders}\n"

    # Additional metrics or top senders, if needed
    top_senders = {}
    for log in weekly_logs:
        sender_id = log['sender_id']
        top_senders[sender_id] = top_senders.get(sender_id, 0) + 1
    
    top_senders = sorted(top_senders.items(), key=lambda x: x[1], reverse=True)[:5]  # Get top 5 senders
    if top_senders:
        summary += "\n🏅 Top Senders:\n"
        for sender_id, count in top_senders:
            summary += f"   {html.escape(str(sender_id))}: {count} messages\n"

    # Send the summary to the user
    await update.message.reply_text(summary, parse_mode=ParseMode.HTML)

async def ocr_debug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("⚠️ Please send an image to perform OCR.")
        return

    photo = update.message.photo[-1]
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tf:
        await photo.get_file().download_to_drive(tf.name)
        extracted_text = pytesseract.image_to_string(tf.name)

    await update.message.reply_text(f"📝 OCR Extracted Text:\n\n{extracted_text}", parse_mode=ParseMode.MARKDOWN)
