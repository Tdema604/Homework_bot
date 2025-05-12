import os
import tempfile
import logging
import pytesseract
from PIL import Image
from telegram import Message
from telegram.ext import ContextTypes
from telegram.constants import ChatAction
from typing import Dict
from datetime import datetime
from telegram import Update, MessageEntity
from telegram.ext import ContextTypes

from utils import (
    is_admin,
    extract_text_from_image,
    transcribe_audio,
    is_homework_text,
    forward_homework,
    get_activity_summary,
    clear_homework_log,
    track_sender_activity,
    list_sender_activity,
    clear_sender_data,
    add_route_to_env,
    delete_route_from_env
)

# ======================== Core Functions ========================
def get_dynamic_greeting():
    """Replacement for the missing greeting function"""
    current_hour = datetime.now().hour
    if 5 <= current_hour < 12:
        return "Good morning! 🌅"
    elif 12 <= current_hour < 17:
        return "Good afternoon! ☀️"
    elif 17 <= current_hour < 21:
        return "Good evening! 🌆"
    return "Good night! 🌙"

async def notify_admins(context: ContextTypes.DEFAULT_TYPE, message: str):
    """Send notifications to all admins"""
    for admin_id in context.bot_data.get("ADMIN_CHAT_IDS", []):
        try:
            await context.bot.send_message(admin_id, message)
        except Exception as e:
            logging.error(f"Failed to notify admin {admin_id}: {e}")

# ======================== Command Handlers ========================
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    greeting = get_dynamic_greeting()
    await update.message.reply_text(
        f"{greeting}, {update.effective_user.first_name}!\n"
        "I'm your Homework Forwarding Bot. Use /help for commands."
    )
async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Your chat ID: {update.effective_chat.id}")
    
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
📚 <b>Available Commands:</b>

👤 <u>User Commands</u>
/start - Start the bot
/id - Show your chat ID
/feedback - Send feedback

🛠️ <u>Admin Commands</u>
/list_routes - Show forwarding routes
/add_route &lt;from_id&gt; &lt;to_id&gt; - Add new route
/delete_route &lt;from_id&gt; - Remove route
/weekly_summary - Get homework stats
/list_senders - Show activity log
"""
    await update.message.reply_text(help_text, parse_mode="HTML")

async def add_routes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await update.message.reply_text("❌ Admin only!")
    
    try:
        src, dst = map(int, context.args[:2])
        context.bot_data.setdefault("ROUTES_MAP", {})[src] = dst
        add_route_to_env(src, dst)
        await update.message.reply_text(f"✅ Route added: {src} → {dst}")
    except (ValueError, IndexError):
        await update.message.reply_text("⚠️ Usage: /add_route <from_id> <to_id>")

async def delete_routes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await update.message.reply_text("❌ Admin only!")
    
    try:
        src = int(context.args[0])
        if src in context.bot_data.get("ROUTES_MAP", {}):
            del context.bot_data["ROUTES_MAP"][src]
            delete_route_from_env(src)
            await update.message.reply_text(f"🗑️ Deleted route: {src}")
        else:

            await update.message.reply_text("⚠️ Route not found")
    except (ValueError, IndexError):
        await update.message.reply_text("⚠️ Usage: /delete_route <from_id>")

            await update.message.reply_text("⚠️ Route not found.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error deleting route: {e}")

async def reload_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    try:
        context.bot_data["ROUTES_MAP"] = parse_routes_map(os.getenv("ROUTES_MAP", ""))
        await update.message.reply_text("✅ Configuration reloaded.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def get_weekly_summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    summary = get_weekly_summary(context)
    await update.message.reply_text(summary or "📭 No homework forwarded this week.")

async def clear_homework_log_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    clear_homework_log(context.application.bot_data)
    await update.message.reply_text("🧹 Cleared homework log!")

async def list_senders_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    
    # Extract bot_data from the context
    bot_data = context.application.bot_data
    
    # Pass the bot_data to the list_sender_activity function
    activity_summary = list_sender_activity(bot_data)
    
    # Send the activity summary as a reply
    await update.message.reply_text(activity_summary)


async def clear_senders_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    clear_sender_data(context)
    await update.message.reply_text("🧼 Cleared sender activity log.")

# ========================= Feedback =========================

async def feedback_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📝 Please reply to this message with your feedback.")

# ======================== Message Handling ========================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main message processing pipeline"""
    if not update.message or update.message.via_bot:
        return

    # Skip command processing
    if update.message.entities and any(e.type == MessageEntity.BOT_COMMAND for e in update.message.entities):
        return

    track_sender_activity(update, context)
    routes = context.bot_data.get("ROUTES_MAP", {})
    message = update.message

    # Text message processing
    if message.text and is_homework_text(message.text):
        await forward_homework(context, message, routes)
        return

    # Photo with caption/OCR
    if message.photo:
        if message.caption and is_homework_text(message.caption):
            await forward_homework(context, message, routes)
            return
        
        try:
            photo_file = await message.photo[-1].get_file()
            image_path = await photo_file.download_to_drive()
            extracted_text = extract_text_from_image(str(image_path))
            if is_homework_text(extracted_text):
                await forward_homework(context, message, routes)
        except Exception as e:
            logging.error(f"OCR failed: {e}")

    # Audio processing
    elif message.voice or message.audio:
        try:
            transcript = await transcribe_audio_with_whisper(message, context)
            if transcript and is_homework_text(transcript):
                await forward_homework(context, message, routes)
        except Exception as e:
            logging.error(f"Transcription failed: {e}")

    if not update.message or update.message.via_bot:
        return

    # Skip commands
    if update.message.entities and any(e.type == MessageEntity.BOT_COMMAND for e in update.message.entities):
        return

    # Track activity
    context.bot_data.setdefault("SENDER_ACTIVITY", {})[update.effective_user.id] = {
        "name": update.effective_user.full_name,
        "last_active": datetime.now().isoformat()
    }

    # Process message
    routes = context.bot_data.get("ROUTES_MAP", {})
    if update.message.chat_id not in routes:
        return

    # Forward if homework detected
    if (update.message.text and is_homework_text(update.message.text)) or \
       (update.message.caption and is_homework_text(update.message.caption)):
        await forward_homework(context, update.message, routes)
        return

    # Process media
    if update.message.photo:
        try:
            photo_file = await update.message.photo[-1].get_file()
            with tempfile.NamedTemporaryFile(suffix='.jpg') as tmp:
                await photo_file.download_to_drive(tmp.name)
                if is_homework_text(await extract_text_from_image(tmp.name)):
                    await forward_homework(context, update.message, routes)
        except Exception as e:
            logging.error(f"Photo processing failed: {e}")

# Configure Tesseract for Dzongkha
pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'
TESSDATA_PREFIX = '/usr/share/tesseract-ocr/4.00/tessdata'

def setup_dzongkha_ocr():
    """Ensure Dzongkha language support is available"""
    dzo_path = f"{TESSDATA_PREFIX}/dzo.traineddata"
    if not os.path.exists(dzo_path):
        os.makedirs(TESSDATA_PREFIX, exist_ok=True)
        os.system(f"wget https://github.com/tesseract-ocr/tessdata/raw/main/dzo.traineddata -O {dzo_path}")

async def extract_text_from_image(image_path: str) -> str:
    """Extract text from images with Dzongkha support"""
    try:
        setup_dzongkha_ocr()
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img, lang='dzo+eng')
        return text.strip()
    except Exception as e:
        logging.error(f"OCR failed: {e}")
        return ""

async def forward_homework(
    context: ContextTypes.DEFAULT_TYPE,
    message: Message,
    routes_map: Dict[int, int]
) -> bool:
    """Enhanced forwarding logic"""
    target_chat = routes_map.get(message.chat_id)
    if not target_chat:
        return False

    try:
        await context.bot.send_chat_action(target_chat, ChatAction.TYPING)
        
        if message.text:
            await context.bot.send_message(
                chat_id=target_chat,
                text=f"📝 Homework from {message.from_user.full_name}:\n\n{message.text}"
            )
            return True

        elif message.photo:
            with tempfile.NamedTemporaryFile(suffix='.jpg') as tmp:
                await message.photo[-1].get_file().download_to_drive(tmp.name)
                ocr_text = await extract_text_from_image(tmp.name)
                
                if ocr_text:
                    await context.bot.send_message(
                        chat_id=target_chat,
                        text=f"📸 Image content:\n\n{ocr_text}"
                    )
                
                await context.bot.send_photo(
                    chat_id=target_chat,
                    photo=message.photo[-1].file_id,
                    caption=f"From {message.from_user.full_name}" + (
                        f"\n\n{message.caption}" if message.caption else ""
                    )
                )
            return True

    except Exception as e:
        logging.error(f"Forwarding error: {e}")
    
    return False

# ======================== Handler Registration ========================
def register_handlers(application):
    """Consistent handler registration"""
    handlers = [
        CommandHandler("start", start_handler),
        CommandHandler("help", help_command),
        CommandHandler("id", id_command),
        CommandHandler("list_routes", list_routes_command),
        CommandHandler("add_route", add_routes_command),
        CommandHandler("delete_route", delete_routes_command),
        CommandHandler("weekly_summary", get_weekly_summary_command),
        CommandHandler("list_senders", list_senders_command),
        CommandHandler("feedback", feedback_command),
        MessageHandler(filters.ALL & ~filters.COMMAND, handle_message)
    ]
    
    for handler in handlers:
        application.add_handler(handler)
