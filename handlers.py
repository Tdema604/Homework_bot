import os
import logging
from datetime import datetime
from telegram import Update, MessageEntity
from telegram.ext import ContextTypes

from utils import (
    is_admin,
    extract_text_from_image,
    transcribe_audio_with_whisper,
    is_homework_text,
    forward_homework,
    get_weekly_summary,
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
