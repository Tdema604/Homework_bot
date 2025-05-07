import logging
import os
import time
import html
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from utils import (
    escape_markdown,
    get_media_type_icon,
    is_homework,
    load_routes_from_env,
    save_routes_to_env,
    get_routes_map,
)

logger = logging.getLogger(__name__)

# === Time Helpers ===
def get_local_bhutan_time():
    return datetime.now(ZoneInfo("Asia/Thimphu"))

def get_dynamic_greeting():
    hour = get_local_bhutan_time().hour
    if hour < 12:
        return "Good morning! 🌞"
    elif hour < 18:
        return "Good afternoon! 🌅"
    return "Good evening! 🌙"

def get_bot_mood():
    day = get_local_bhutan_time().weekday()
    if day == 6:
        return "I'm feeling sleepy today 😴"
    elif day == 5:
        return "It's the weekend! Yay! 🎉"
    return "I'm ready to help! 🤩"

# === Command Handlers ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Hello, {user.first_name or 'there'}!\n"
        f"{get_dynamic_greeting()}\n\n"
        "🔔 Tip: Use /summary to get today’s homework again!\n\n"
        f"{get_bot_mood()}\n"
        "I'm your Homework Forwarder Bot. Drop homework, and I’ll pass it along!"
    )
    logger.info("✅ /start command triggered.")

async def chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"🆔 Chat ID: `{update.effective_chat.id}`",
        parse_mode="Markdown",
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    routes = context.bot_data.get("ROUTES_MAP", {})
    await update.message.reply_text(
        "✅ <b>Bot Status</b>\n"
        f"• <b>Uptime:</b> always-on (webhook)\n"
        f"• <b>Active Routes:</b> {len(routes)} source-to-target mappings\n"
        f"• <b>Admin Chat IDs:</b> {context.bot_data.get('ADMIN_CHAT_IDS', [])}",
        parse_mode="HTML"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    admin_ids = context.bot_data.get("ADMIN_CHAT_IDS", [])
    if user_id in admin_ids:
        help_text = (
            "👋 <b>Admin Help Menu</b>\n\n"
            "/start – Greet the bot\n"
            "/status – Bot health check\n"
            "/chatid – Get chat ID\n"
            "/list_routes – List all routes\n"
            "/add_routes [src] [dest] – Add a new route\n"
            "/remove_routes [src] – Remove a route\n"
            "/reload_config – Reload routes from .env\n"
            "/weekly_summary – Get a 7-day homework report\n"
            "/clear_homework_log – Clear the homework log\n"
            "/list_senders – View recent sender activity\n"
            "/clear_senders – Clear sender activity"
        )
    else:
        help_text = (
            "👋 <b>Parent/Teacher Help Menu</b>\n\n"
            "/start – Greet the bot\n"
            "/status – Check if the bot is online\n"
            "/summary – Get today's homework summary\n\n"
            "<i>This bot automatically forwards homework from teachers to parents.</i>"
        )
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)

async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = update.effective_chat.id
    routes = context.bot_data.get("ROUTES_MAP", {})
    sender_activity = context.bot_data.setdefault("SENDER_ACTIVITY", {})
    forwarded_logs = context.bot_data.setdefault("FORWARDED_LOGS", [])

    if message.text and "/nayavpn_shopbot@" in message.text:
        return

    sender = update.effective_user
    sender_activity[sender.id] = {
        "name": sender.full_name,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "last_message": message.text or message.caption or "📎 Media",
    }

    if chat_id not in routes:
        return

    target_chat_id = routes[chat_id]
    forwarded_msg = None

    try:
        escaped_text = html.escape(message.text or message.caption or "")
        if message.text:
            forwarded_msg = await context.bot.send_message(
                chat_id=target_chat_id,
                text=escaped_text,
                parse_mode=ParseMode.HTML,
            )
        elif message.photo:
            forwarded_msg = await context.bot.send_photo(
                chat_id=target_chat_id,
                photo=message.photo[-1].file_id,
                caption=escaped_text,
                parse_mode=ParseMode.HTML,
            )
        elif message.document:
            forwarded_msg = await context.bot.send_document(
                chat_id=target_chat_id,
                document=message.document.file_id,
                caption=escaped_text,
                parse_mode=ParseMode.HTML,
            )
        elif message.video:
            forwarded_msg = await context.bot.send_video(
                chat_id=target_chat_id,
                video=message.video.file_id,
                caption=escaped_text,
                parse_mode=ParseMode.HTML,
            )
        elif message.audio:
            forwarded_msg = await context.bot.send_audio(
                chat_id=target_chat_id,
                audio=message.audio.file_id,
                caption=escaped_text,
                parse_mode=ParseMode.HTML,
            )
        elif message.voice:
            forwarded_msg = await context.bot.send_voice(
                chat_id=target_chat_id,
                voice=message.voice.file_id,
                caption=escaped_text,
                parse_mode=ParseMode.HTML,
            )
        elif message.sticker:
            forwarded_msg = await context.bot.send_sticker(
                chat_id=target_chat_id,
                sticker=message.sticker.file_id,
            )

        if is_homework(message):
            media_type_emoji = get_media_type_icon(message)
            content = f"{media_type_emoji} {escaped_text}" if escaped_text else media_type_emoji
            forwarded_logs.append({
                "timestamp": time.time(),
                "sender": sender.full_name,
                "type": media_type_emoji,
                "content": content,
            })

    except Exception as e:
        logger.exception("Forwarding failed: %s", e)

# Route Management, Logging, Admin Functions unchanged...

# (You already pasted all of these and they are valid!)