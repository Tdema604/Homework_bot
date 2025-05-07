import logging
import os
import time
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
    get_route_map,
)

# Setup logging
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

# === Forwarding Handler ===
async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Protect command messages like /start from being intercepted
    if update.message and update.message.text and update.message.text.startswith("/"):
        return

    # Your existing message forwarding logic here
    # For example:
    msg = update.message
    if not msg:
        return

    # Skip forwarding junk messages
    if msg.text and "/nayavpn_shopbot" in msg.text:
        return

    # Access routing config
    route_map = context.bot_data.get("ROUTES_MAP", {})
    allowed_sources = context.bot_data.get("ALLOWED_SOURCE_CHAT_IDS", [])

    source_chat_id = update.effective_chat.id
    if source_chat_id not in allowed_sources:
        return

    # Forward to mapped destinations
    targets = route_map.get(str(source_chat_id), [])
    for target_id in targets:
        try:
            if msg.text:
                await context.bot.send_message(target_id, msg.text)
            elif msg.photo:
                await context.bot.send_photo(target_id, photo=msg.photo[-1].file_id, caption=msg.caption or "")
            elif msg.document:
                await context.bot.send_document(target_id, document=msg.document.file_id, caption=msg.caption or "")
            # Add support for other media types if needed
        except Exception as e:
            logger.error(f"❌ Failed to forward to {target_id}: {e}")

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
    route_map = context.bot_data.get("ROUTE_MAP", {})
    msg = (
        "✅ *Bot Status*\n"
        f"• Uptime: Webhook mode\n"
        f"• Active Routes: {len(route_map)}\n"
        f"• Admin Chat ID: `{os.getenv('ADMIN_CHAT_ID')}`"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def reload_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != int(os.getenv("ADMIN_CHAT_ID", "0")):
        await update.message.reply_text("⛔️ Access denied.")
        return
    try:
        new_map = get_route_map()
        context.bot_data["ROUTE_MAP"] = new_map
        await update.message.reply_text("♻️ Route map reloaded from .env successfully.")
    except Exception as e:
        logger.exception("Reload error:")
        await update.message.reply_text("❌ Reload failed.")

async def list_routes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    routes = context.bot_data.get("ROUTE_MAP", {})
    if not routes:
        await update.message.reply_text("⚠️ No routes configured.")
        return
    msg = "*📚 Active Routes:*\n" + "\n".join(
        f"• `{s}` ➡️ `{t}`" for s, t in routes.items()
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def add_routes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != int(os.getenv("ADMIN_CHAT_ID", "0")):
        await update.message.reply_text("⛔️ Only admin can add routes.")
        return
    try:
        source_id, target_id = map(int, context.args)
        if source_id == target_id:
            await update.message.reply_text("❗ Source and target can't be the same.")
            return
        context.bot_data["ROUTE_MAP"][source_id] = target_id
        save_routes_to_env(context.bot_data["ROUTE_MAP"])
        await update.message.reply_text(
            f"✅ Route added: `{source_id}` ➡️ `{target_id}`", parse_mode="Markdown"
        )
    except Exception:
        await update.message.reply_text("❌ Failed to add route.")

async def remove_routes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != int(os.getenv("ADMIN_CHAT_ID", "0")):
        await update.message.reply_text("⛔️ Only admin can remove routes.")
        return
    try:
        source_id = int(context.args[0])
        if context.bot_data["ROUTE_MAP"].pop(source_id, None):
            save_routes_to_env(context.bot_data["ROUTE_MAP"])
            await update.message.reply_text(
                f"🗑️ Route removed: `{source_id}`", parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("⚠️ No route found for that source ID.")
    except Exception:
        await update.message.reply_text("❗ Error processing command.")

async def weekly_homework(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logs = [
        l
        for l in context.bot_data.get("FORWARDED_LOGS", [])
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
    if update.effective_user.id != int(os.getenv("ADMIN_CHAT_ID", "0")):
        await update.message.reply_text("⛔️ You can't clear this.")
        return
    context.bot_data["FORWARDED_LOGS"] = []
    await update.message.reply_text("✅ Homework log cleared.")

async def clear_senders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != int(os.getenv("ADMIN_CHAT_ID", "0")):
        await update.message.reply_text("⛔️ You are not authorized.")
        return
    context.bot_data["SENDER_ACTIVITY"] = {}
    await update.message.reply_text("✅ Sender log cleared.")

async def list_senders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != int(os.getenv("ADMIN_CHAT_ID", "0")):
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
