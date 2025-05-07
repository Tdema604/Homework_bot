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
        "I'm your Homework Forwarder Bot. Drop homework, and I’ll pass it along!",
        parse_mode=ParseMode.HTML
    )

async def chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"🆔 Chat ID: <code>{update.effective_chat.id}</code>",
        parse_mode=ParseMode.HTML,
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    routes = context.bot_data.get("ROUTES_MAP", {})
    await update.message.reply_text(
        "✅ <b>Bot Status</b>\n"
        f"• <b>Uptime:</b> always-on (webhook)\n"
        f"• <b>Active Routes:</b> {len(routes)} source-to-target mappings\n"
        f"• <b>Admin Chat IDs:</b> {context.bot_data.get('ADMIN_CHAT_IDS', [])}",
        parse_mode=ParseMode.HTML
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

# === Admin Utilities ===
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
    await update.message.reply_text(f"🗓️ <b>Last 7 Days Summary</b>\n\n{formatted}", parse_mode=ParseMode.HTML)

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