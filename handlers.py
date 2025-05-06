import os
import logging
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from utils import (
    save_routes_to_file,
    load_routes_from_file,
    is_homework,
    get_route_map,
    load_env,
    get_media_type_icon,
    escape_markdown,
)

logger = logging.getLogger(__name__)
ROUTE_MAP = get_route_map()

def get_route_map():
    try:
        with open("routes.json", "r", encoding="utf-8") as f:
            raw_map = json.load(f)

        route_map = {}
        repaired = False

        for source, targets in raw_map.items():
            if not isinstance(targets, list):
                targets = [targets]
                repaired = True
            route_map[int(source)] = [int(t) for t in targets]

        # 🔧 Auto-repair routes.json if needed
        if repaired:
            with open("routes.json", "w", encoding="utf-8") as f:
                fixed_map = {str(k): v for k, v in route_map.items()}
                json.dump(fixed_map, f, indent=2)
            print("🔧 Auto-repaired routes.json format ✅")

        return route_map

    except Exception as e:
        print(f"❌ Failed to load route map: {e}")
        return {}

# Local Bhutan Time Helper 
def get_local_bhutan_time():
    return datetime.now(ZoneInfo("Asia/Thimphu"))

# Dynamic Greeting Based on Time
def get_dynamic_greeting():
    current_hour = get_local_bhutan_time().hour
    if current_hour < 12:
        return "Good morning! 🌞"
    elif current_hour < 18:
        return "Good afternoon! 🌅"
    else:
        return "Good evening! 🌙"
# Bot Mood Based on Day of Week 
def get_bot_mood():
    current_day = get_local_bhutan_time().weekday()
    if current_day == 6:
        return "I'm feeling sleepy today 😴"
    elif current_day == 5:
        return "It's the weekend! Yay! 🎉"
    else:
        return "I'm ready to help! 🤩"

#  Notify Admin 
async def notify_admin(application, admin_chat_id, webhook_url):
    route_map = application.bot_data.get("ROUTE_MAP")
    if route_map:
        await application.bot.send_message(
            admin_chat_id,
            f"🤖 Bot restarted.\n🗺️ Active Routes: {len(route_map)} source-to-target mappings\n🌐 Webhook URL: {webhook_url}"
        )
    else:
        await application.bot.send_message(
            admin_chat_id,
            f"🤖 Bot restarted.\n🗺️ Active Routes: 0\n🌐 Webhook URL: {webhook_url}"
        )

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    greeting = get_dynamic_greeting()
    mood = get_bot_mood()
    await update.message.reply_text(
        f"👋 Hello, {user.first_name}!\n"
        f"{greeting}\n\n"
        f"🔔 Tip: If you ever miss a message, just type /summary to get today's homework again!\n\n"
        f"{mood}\n"
        "I'm your Homework Forwarder Bot. Drop homework, and I’ll pass it along!"
    )

# /id 
async def chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🆔 Chat ID: `{update.effective_chat.id}`", parse_mode="Markdown")

# /status 
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    route_map = load_routes_from_file()
    admin_id = context.bot_data.get("ADMIN_CHAT_ID")
    await update.message.reply_text(
        f"✅ *Bot Status*\n• Uptime: webhook\n• Active Routes: {len(route_map)}\n• Admin Chat ID: {admin_id}",
        parse_mode="Markdown"
    )

# /reload 
async def reload_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != context.bot_data.get("ADMIN_CHAT_ID"):
        await update.message.reply_text("⛔️ Access denied.")
        return
    try:
        load_env()
        global ROUTE_MAP
        ROUTE_MAP = get_route_map()
        context.bot_data["ROUTE_MAP"] = ROUTE_MAP
        await update.message.reply_text("♻️ Config reloaded successfully.")
    except Exception as e:
        logger.exception("Reload failed")
        await update.message.reply_text("❌ Reload failed.")

# /listroutes 
async def list_routes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    routes = context.bot_data.get("ROUTE_MAP", {})
    if not routes:
        await update.message.reply_text("⚠️ No routes configured yet.")
        return
    msg = "*📚 Active Routes:*\n"
    msg += "\n".join([f"• `{k}` ➡️ `{v}`" for k, v in routes.items()])
    await update.message.reply_text(msg, parse_mode="Markdown")

# /addroutes 
async def add_routes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != context.bot_data.get("ADMIN_CHAT_ID"):
        await update.message.reply_text("⛔️ Only admin can add routes.")
        return
    try:
        source_id, target_id = map(int, context.args)
        if source_id == target_id:
            return await update.message.reply_text("❗ Source and Target can't be the same.")
        context.bot_data["ROUTE_MAP"][source_id] = target_id
        save_routes_to_file(context.bot_data["ROUTE_MAP"])
        await update.message.reply_text(f"✅ Route added: `{source_id}` ➡️ `{target_id}`", parse_mode="Markdown")
    except:
        await update.message.reply_text("❗ Usage: /addroutes <source_id> <target_id>")

# /removeroute 
async def remove_routes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != context.bot_data.get("ADMIN_CHAT_ID"):
        return await update.message.reply_text("⛔️ Only admin can remove routes.")
    try:
        source_id = int(context.args[0])
        if source_id in context.bot_data["ROUTE_MAP"]:
            del context.bot_data["ROUTE_MAP"][source_id]
            save_routes_to_file(context.bot_data["ROUTE_MAP"])
            await update.message.reply_text(f"🗑️ Removed route for `{source_id}`", parse_mode="Markdown")
        else:
            await update.message.reply_text("⚠️ Route not found.")
    except:
        await update.message.reply_text("❗ Usage: /removeroute <source_id>", parse_mode="Markdown")

# /list_senders 
async def list_senders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != context.bot_data.get("ADMIN_CHAT_ID"):
        return await update.message.reply_text("⛔️ Access denied.")
    logs = context.bot_data.get("FORWARDED_LOGS", [])
    if not logs:
        return await update.message.reply_text("No messages have been forwarded yet.")
    msg = "*📨 Sender Activity Summary:*\n"
    for log in logs:
        msg += f"\n🕓 {log['timestamp']} | {log['type']} | From: {log['sender']}"
    await update.message.reply_text(msg, parse_mode="Markdown")

# /clear_senders 
async def clear_senders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.bot_data["SENDER_LOGS"] = []
    await update.message.reply_text("✅ Sender log cleared.")

# /weekly_homework 
async def weekly_homework(update: Update, context: ContextTypes.DEFAULT_TYPE):
    one_week_ago = time.time() - 7 * 24 * 60 * 60
    logs = [log for log in context.bot_data.get("FORWARDED_LOGS", []) if
            datetime.strptime(log["timestamp"], "%Y-%m-%d %H:%M:%S").timestamp() >= one_week_ago]
    if not logs:
        return await update.message.reply_text("No homework in the last 7 days.")
    summary = "*📚 Weekly Homework Summary*\n"
    for log in logs:
        summary += f"\n🗓 {log['timestamp']} | {log['type']}\nFrom: {log['sender']}\n📝 {escape_markdown(log['content'])}\n"
    await update.message.reply_text(summary, parse_mode="MarkdownV2")

# /clear_homework 
async def clear_homework_log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != context.bot_data.get("ADMIN_CHAT_ID"):
        return await update.message.reply_text("⛔️ Access denied.")
    context.bot_data["FORWARDED_LOGS"] = []
    await update.message.reply_text("✅ Homework log cleared.")

# Forward Message 
async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        msg = update.message
        if not msg:
            return

        source_id = msg.chat_id
        target_id = context.bot_data.get("ROUTE_MAP", {}).get(source_id)
        if not target_id:
            return

        junk_keywords = ["/nayavpn", "@shopbot", "promotion", "win prize"]
        if msg.text and any(junk in msg.text.lower() for junk in junk_keywords):
            logger.info("🚫 Junk message blocked.")
            return

        content, media_type = "", None
        if msg.text:
            content, media_type = msg.text, "text"
            await context.bot.send_message(target_id, msg.text)
        elif msg.photo:
            media_type = "photo"
            await context.bot.send_photo(target_id, msg.photo[-1].file_id)
        elif msg.document:
            media_type = "document"
            await context.bot.send_document(target_id, msg.document.file_id)
        elif msg.audio:
            media_type = "audio"
            await context.bot.send_audio(target_id, msg.audio.file_id)
        elif msg.video:
            media_type = "video"
            await context.bot.send_video(target_id, msg.video.file_id)
        elif msg.voice:
            media_type = "voice"
            await context.bot.send_voice(target_id, msg.voice.file_id)
        elif msg.sticker:
            media_type = "sticker"
            await context.bot.send_sticker(target_id, msg.sticker.file_id)

        log = {
            "sender": msg.from_user.full_name,
            "type": media_type,
            "content": content or media_type,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        context.bot_data.setdefault("FORWARDED_LOGS", []).append(log)
        logger.info(f"✅ Forwarded: {media_type} from {source_id} to {target_id}")

    except Exception as e:
        logger.error(f"🚨 Error forwarding: {e}")
