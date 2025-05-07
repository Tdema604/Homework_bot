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

    # Block spammy bots
    if message.text and "/nayavpn_shopbot@" in message.text:
        return

    # Track sender activity
    sender = update.effective_user
    sender_activity[sender.id] = {
        "name": sender.full_name,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "last_message": message.text or message.caption or "📎 Media",
    }

    # Check if chat is in routes
    if chat_id not in routes:
        return

    target_chat_id = routes[chat_id]
    forwarded_msg = None

    try:
        # Escape special characters for safe display
        escaped_text = escape(message.text or message.caption or "")

# Escape text/caption for HTML
    caption_html = html.escape(message.caption or message.text or "")

        if message.text:
            forwarded_msg = await context.bot.send_message(
                chat_id=target_chat_id, text=escaped_text, parse_mode=ParseMode.HTML
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

        # Log forwarded homework
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
        print("Forwarding failed:", e)


# === Route Management Commands ===
async def reload_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in context.bot_data.get("ADMIN_CHAT_IDS", []):
        await update.message.reply_text("⛔️ Access denied.")
        return
    try:
        new_map = get_routes_map()
        context.bot_data["ROUTES_MAP"] = new_map
        await update.message.reply_text("♻️ Route map reloaded from .env successfully.")
    except Exception as e:
        logger.exception("Reload error:")
        await update.message.reply_text("❌ Reload failed.")



async def list_routes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in context.bot_data.get("ADMIN_CHAT_IDS", []):
        await update.message.reply_text("⛔️ Only admin can list routes.")
        return
    routes = context.bot_data.get("ROUTES_MAP", {})
    if not routes:
        await update.message.reply_text("⚠️ No routes configured.")
        return
    msg = "*📚 Active Routes:*\n" + "\n".join(
        f"• `{s}` ➡️ `{t}`" for s, t in routes.items()
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def add_routes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in context.bot_data.get("ADMIN_CHAT_IDS", []):
        await update.message.reply_text("⛔️ Only admin can add routes.")
        return
    try:
        source_id, target_id = map(int, context.args)
        if source_id == target_id:
            await update.message.reply_text("❗ Source and target can't be the same.")
            return
        context.bot_data["ROUTES_MAP"][source_id] = target_id
        save_routes_to_env(context.bot_data["ROUTES_MAP"])
        await update.message.reply_text(
            f"✅ Routes added: `{source_id}` ➡️ `{target_id}`", parse_mode="Markdown"
        )
    except Exception:
        await update.message.reply_text("❌ Failed to add routes.")

async def remove_routes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in context.bot_data.get("ADMIN_CHAT_IDS", []):
        await update.message.reply_text("⛔️ Only admin can remove routes.")
        return
    try:
        source_id = int(context.args[0])
        if context.bot_data["ROUTES_MAP"].pop(source_id, None):
            save_routes_to_env(context.bot_data["ROUTES_MAP"])
            await update.message.reply_text(
                f"🗑️ Route removed: `{source_id}`", parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("⚠️ No route found for that source ID.")
    except Exception:
        await update.message.reply_text("❗ Error processing command.")

# === Logs and Activity Commands ===
async def weekly_homework(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logs = [
        l for l in context.bot_data.get("FORWARDED_LOGS", [])
        if l["timestamp"] >= time.time() - 7 * 86400
    ]
    if not logs:
        await update.message.reply_text("No homework entries in the last 7 days.")
        return
    msg = "*📚 Weekly Homework Summary*"
    for l in logs:
        t = datetime.fromtimestamp(l["timestamp"]).strftime("%Y-%m-%d %H:%M")
        msg += (
            f"\n🗓 {t} | {l['type']}\nFrom: {l['sender']}\n📝 {escape_markdown(l['content'])}"
        )
    await update.message.reply_text(msg, parse_mode="MarkdownV2")

async def clear_homework_log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in context.bot_data.get("ADMIN_CHAT_IDS", []):
        await update.message.reply_text("⛔️ You can't clear this.")
        return
    context.bot_data["FORWARDED_LOGS"] = []
    await update.message.reply_text("✅ Homework log cleared.")

async def clear_senders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in context.bot_data.get("ADMIN_CHAT_IDS", []):
        await update.message.reply_text("⛔️ You are not authorized.")
        return
    context.bot_data["SENDER_ACTIVITY"] = {}
    await update.message.reply_text("✅ Sender log cleared.")

async def list_senders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in context.bot_data.get("ADMIN_CHAT_IDS", []):
        await update.message.reply_text("⛔️ You are not authorized.")
        return
    activity = context.bot_data.get("SENDER_ACTIVITY", {})
    if not activity:
        await update.message.reply_text("ℹ️ No sender activity.")
        return
    sorted_items = sorted(activity.items(), key=lambda x: x[1]["timestamp"], reverse=True)
    lines = ["🧾 *Recent Sender Activity:*"]
    for uid, info in sorted_items[:30]:
        name = escape_markdown(info["name"])
        msg = escape_markdown(info["last_message"][:50])
        ts = escape_markdown(info["timestamp"])
        lines.append(f"• [{name}](tg://user?id={uid}) - _{ts}_\n  └ \"{msg}\"")
    await update.message.reply_text("\n".join(lines), parse_mode="MarkdownV2")
