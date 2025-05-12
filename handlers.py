import os
import tempfile
import logging
import pytesseract
import subprocess
from PIL import Image
from telegram import Update, Message
from telegram.ext import ContextTypes, CommandHandler
from telegram.constants import ChatAction
from typing import Dict
from datetime import datetime
from telegram import Update, MessageEntity
from utils import (
    is_admin,
    get_dynamic_greeting,
    transcribe_audio,
    is_homework_text,
    forward_homework,
    get_activity_summary,
    clear_homework_log,
    track_sender_activity,
    list_sender_activity,track_sender_activity,
    clear_sender_data,
    add_route_to_env,
    delete_route_from_env
)

from ocr import extract_text_from_image
from audio_utils import extract_text_from_audio, extract_text_from_video

# ======================== Core Functions ========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        greeting = get_dynamic_greeting()
        await update.message.reply_text(f"{greeting} I'm your Homework Bot! 📚")

async def notify_admins(context: ContextTypes.DEFAULT_TYPE, message: str):
    """Send notifications to all admins"""
    for admin_id in context.bot_data.get("ADMIN_CHAT_IDS", []):
        try:
            await context.bot.send_message(admin_id, message)
        except Exception as e:
            logging.error(f"Failed to notify admin {admin_id}: {e}")

# ======================== Command Handlers ========================
# /start command
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    greeting = get_dynamic_greeting()
    await update.message.reply_text(
        f"<b>{greeting}, {update.effective_user.first_name}!</b>\n"
        "I'm your Homework Forwarding Bot. Use <code>/help</code> to view available commands.",
        parse_mode="HTML"
    )

# /id command
async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"<b>Your chat ID:</b> <code>{update.effective_chat.id}</code>",
        parse_mode="HTML"
    )

# /status command
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logging.info(f"📥 /status from {user.username or user.id}")

    route_map = load_routes_from_file()
    active_routes = len(route_map)

    status_msg = (
        "<b>✅ Bot Status</b>\n"
        "• <b>Uptime:</b> Always-on (Webhook Mode)\n"
        f"• <b>Active Routes:</b> {active_routes} source-to-target mappings\n"
        f"• <b>Admin Chat ID:</b> <code>{context.bot_data.get('ADMIN_CHAT_ID')}</code>"
    )

    await update.message.reply_text(status_msg, parse_mode="HTML")

# /help command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    general_help = """
<b>🤖 Homework Forwarder Bot Help</b>

<b>👤 General Users:</b>
- <code>/start</code> – Greet the bot
- <code>/help</code> – Show this help message
- <code>/status</code> – Check bot health/status
- <code>/id</code> – View your chat ID
- Post homework (text, image, or audio) – the bot forwards it automatically.

<b>📢 Teacher Feedback:</b>
- Send feedback to the bot – it will reach the parent group. 🎤📝

Need help? Ping the admin. You’re doing great! 💪
"""

    admin_addon = """
<b>🛡 Admins Only:</b>
- <code>/add_route &lt;from_id&gt; &lt;to_id&gt;</code> – Add a forwarding route
- <code>/delete_route &lt;from_id&gt;</code> – Remove a route
- <code>/list_routes</code> – Show all current routes
- <code>/reload_config</code> – Reload bot config and routing
- <code>/weekly_summary</code> – Show forwarded homework summary
- <code>/clear_homework_log</code> – Clear all homework logs
- <code>/list_senders</code> – View recent sender activity
- <code>/clear_senders</code> – Clear sender log
"""

    help_message = general_help + (admin_addon if user_id in ADMIN_CHAT_IDS else "")
    await update.message.reply_text(help_message.strip(), parse_mode="HTML")

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

# ========================= ROUTES COMMAND =========================
async def add_routes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await update.message.reply_text("❌ Admin only!")

    try:
        src, dst = map(int, context.args[:2])
        context.bot_data.setdefault("ROUTES_MAP", {})[src] = dst
        add_route_to_env(src, dst)
        await update.message.reply_text(f"✅ Route added:\n{src} → {dst}")
    except (ValueError, IndexError):
        await update.message.reply_text("⚠️ Usage: /add_route <from_id> <to_id>")


async def delete_routes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await update.message.reply_text("❌ Admin only!")

    try:
        src = int(context.args[0])
        route_map = context.bot_data.get("ROUTES_MAP", {})
        if src in route_map:
            del route_map[src]
            remove_route_from_env(src)
            await update.message.reply_text(f"✅ Route deleted for: {src}")
        else:
            await update.message.reply_text("⚠️ No such route found.")
    except (ValueError, IndexError):
        await update.message.reply_text("⚠️ Usage: /delete_route <from_id>")


async def list_routes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await update.message.reply_text("❌ Admin only!")

    route_map = context.bot_data.get("ROUTES_MAP", {})
    if not route_map:
        return await update.message.reply_text("ℹ️ No routes defined.")

    message = "📋 Current Routes:\n"
    for src, dst in route_map.items():
        message += f"• {src} → {dst}\n"
    await update.message.reply_text(message)


async def reload_config_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await update.message.reply_text("❌ Admin only!")

    context.bot_data["ROUTES_MAP"] = parse_routes_map(os.getenv("ROUTES_MAP", ""))
    await update.message.reply_text("🔁 Config reloaded from .env")


# --- Feedback Command --- #
async def feedback_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle feedback submission from teachers."""
    try:
        # Check if a message is included
        if len(context.args) == 0:
            await update.message.reply_text("⚠️ Please provide your feedback after the command.")
            return
        
        feedback = " ".join(context.args)
        user = update.effective_user
        timestamp = datetime.now().isoformat()

        # Log feedback in bot data (Could also save to a file or database in a real system)
        context.bot_data.setdefault("FEEDBACK", []).append({
            "user_id": user.id,
            "name": user.full_name,
            "feedback": feedback,
            "timestamp": timestamp
        })

        # Acknowledge receipt of feedback
        await update.message.reply_text("✅ Your feedback has been submitted. Thank you!")

        # Optionally, log or notify admins about the feedback
        if is_admin(update, context):
            feedback_summary = f"New feedback from {user.full_name}:\n\n{feedback}\n\nTimestamp: {timestamp}"
            # Send feedback summary to admins
            for admin_chat_id in context.bot_data.get("ADMIN_CHAT_IDS", []):
                await context.bot.send_message(admin_chat_id, feedback_summary)

    except Exception as e:
        await update.message.reply_text(f"❌ Something went wrong while processing your feedback. Error: {e}")
        logger.error(f"Feedback command failed: {e}")

# ======================== Configure Tesseract for Dzongkha ========================
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

# ========================= Forwarding Homework =========================
async def forward_homework(
    context: ContextTypes.DEFAULT_TYPE,
    message: Message,
    routes_map: Dict[int, int]
) -> bool:
    """Enhanced forwarding logic to handle text, images, audio, voice, and video"""
    target_chat = routes_map.get(message.chat_id)
    if not target_chat:
        logging.warning(f"No route found for {message.chat_id}")
        return False

    await context.bot.send_chat_action(target_chat, ChatAction.TYPING)

    # Safeguards
    ocr_text = audio_text = voice_text = video_text = transcript = None
    forwarded = False

    def format_caption(user, caption):
        return f"From {user.full_name}" + (f"\n\n{caption}" if caption else "")

    try:
        if message.text:
            # Process text message
            await context.bot.send_message(
                chat_id=target_chat,
                text=f"📝 Homework from {message.from_user.full_name}:\n\n{message.text}"
            )
            transcript = message.text
            forwarded = True

        elif message.photo:
            # Process image (OCR)
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
                    caption=format_caption(message.from_user, message.caption)
                )
            forwarded = True

        elif message.audio:
            # Process audio (transcribe)
            audio_path = await (await message.audio.get_file()).download()
            audio_text = await extract_text_from_audio(audio_path)

            if audio_text:
                await context.bot.send_message(
                    chat_id=target_chat,
                    text=f"🎧 Audio content:\n\n{audio_text}"
                )

            await context.bot.send_audio(
                chat_id=target_chat,
                audio=message.audio.file_id,
                caption=format_caption(message.from_user, message.caption)
            )
            transcript = audio_text
            forwarded = True

        elif message.voice:
            # Process voice (transcribe)
            voice_path = await (await message.voice.get_file()).download()
            voice_text = await extract_text_from_audio(voice_path)

            if voice_text:
                await context.bot.send_message(
                    chat_id=target_chat,
                    text=f"🎙️ Voice content:\n\n{voice_text}"
                )

            await context.bot.send_voice(
                chat_id=target_chat,
                voice=message.voice.file_id,
                caption=format_caption(message.from_user, message.caption)
            )
            transcript = voice_text
            forwarded = True

        elif message.video:
            # Process video (extract audio & transcribe)
            video_path = await (await message.video.get_file()).download()
            video_text = await extract_text_from_video(video_path)

            if video_text:
                await context.bot.send_message(
                    chat_id=target_chat,
                    text=f"🎥 Video content:\n\n{video_text}"
                )

            await context.bot.send_video(
                chat_id=target_chat,
                video=message.video.file_id,
                caption=format_caption(message.from_user, message.caption)
            )
            transcript = video_text
            forwarded = True

    except Exception as e:
        logging.error(f"Forwarding error: {e}")
        return False

    # ✅ Log successful forwards
    if forwarded:
        context.bot_data.setdefault("FORWARDED_LOGS", []).append({
            "timestamp": datetime.now().isoformat(),
            "text": transcript or ocr_text or "[media]",
            "sender": f"{message.from_user.full_name} ({message.from_user.id})",
            "type": message.effective_attachment.__class__.__name__ if message.effective_attachment else "Text"
        })

    return forwarded



# ============================ MAIN ============================
def main():
    """Start the bot."""
    application = Application.builder().token(os.getenv("TELEGRAM_API_TOKEN")).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("id", id_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("list_routes", list_routes_command))
    application.add_handler(CommandHandler("add_route", add_routes_command))
    application.add_handler(CommandHandler("delete_route", delete_routes_command))
    application.add_handler(CommandHandler("reload_config", reload_config))
    application.add_handler(CommandHandler("weekly_summary", get_weekly_summary_command))
    application.add_handler(CommandHandler("clear_homework_log", clear_homework_log_command))
    application.add_handler(CommandHandler("list_senders", list_senders_command))
    application.add_handler(CommandHandler("clear_senders", clear_senders_command))

# --- Add Command Handler to Application --- #
    feedback_handler = CommandHandler('feedback', feedback_command)
    application.add_handler(feedback_handler)

    application.run_polling()

if __name__ == '__main__':
    main()
