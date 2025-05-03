import logging
from telegram import Update
from telegram.ext import ContextTypes
from utils import is_homework, get_route_map, load_env

logger = logging.getLogger(__name__)

# Global ROUTE_MAP that updates in-memory
ROUTE_MAP = get_route_map()

# /id command
async def chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    await update.message.reply_text(f"Chat ID: {chat.id}", parse_mode="Markdown")

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! I'm your Homework Forwarder Bot. Drop homework, and I'll pass it along!")

# /status command
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = (
        "*Bot Status*\n"
        f"Uptime: Webhook mode\n"
        f"Active Routes: {len(ROUTE_MAP)} mapped\n"
        f"Admin Chat ID: {context.bot_data.get('ADMIN_CHAT_ID')}"
    )
    await update.message.reply_text(status_msg, parse_mode="Markdown")

# /reload command
async def reload_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != context.bot_data.get("ADMIN_CHAT_ID"):
        return await update.message.reply_text("Access denied. Only admin can reload config.")
    
    try:
        load_env()
        global ROUTE_MAP
        ROUTE_MAP = get_route_map()
        await update.message.reply_text("Configuration and route map reloaded.")
    except Exception as e:
        logger.exception("Reload failed:")
        await update.message.reply_text("Failed to reload config.")

# /addroutes command
async def addroutes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != context.bot_data.get("ADMIN_CHAT_ID"):
        return await update.message.reply_text("Access denied.")
    
    text = update.message.text.replace("/addroutes", "").strip()
    global ROUTE_MAP
    count = 0
    for pair in text.split(","):
        if ":" in pair:
            try:
                source, target = map(int, pair.strip().split(":"))
                ROUTE_MAP[source] = target
                count += 1
            except Exception as e:
                logger.warning(f"Failed to parse pair: {pair}")
    await update.message.reply_text(f"✅ Added {count} route(s).")

# /removeroutes command
async def removeroutes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != context.bot_data.get("ADMIN_CHAT_ID"):
        return await update.message.reply_text("Access denied.")
    
    text = update.message.text.replace("/removeroutes", "").strip()
    global ROUTE_MAP
    count = 0
    for sid in text.split(","):
        try:
            sid = int(sid.strip())
            if sid in ROUTE_MAP:
                del ROUTE_MAP[sid]
                count += 1
        except Exception:
            continue
    await update.message.reply_text(f"❌ Removed {count} route(s).")

# Message forwarding logic
async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = update.message
        if not message:
            return

        source_id = message.chat_id
        target_id = ROUTE_MAP.get(source_id)
        admin_id = context.bot_data.get("ADMIN_CHAT_ID")

        if not target_id:
            return

        if message.text and not is_homework(message):
            return

        caption = message.caption or ""
        sender = update.effective_user
        sender_name = f"@{sender.username}" if sender.username else f"user {sender.id}"

        media_type = "Unsupported"
        if message.text:
            await context.bot.send_message(chat_id=target_id, text=message.text)
            media_type = "Text"
        elif message.photo:

await context.bot.send_photo(chat_id=target_id, photo=message.photo[-1].file_id, caption=caption)
            media_type = "Photo"
        elif message.video:
            await context.bot.send_video(chat_id=target_id, video=message.video.file_id, caption=caption)
            media_type = "Video"
        elif message.document:
            await context.bot.send_document(chat_id=target_id, document=message.document.file_id, caption=caption)
            media_type = "Document"
        elif message.audio:
            await context.bot.send_audio(chat_id=target_id, audio=message.audio.file_id, caption=caption)
            media_type = "Audio"
        elif message.voice:
            await context.bot.send_voice(chat_id=target_id, voice=message.voice.file_id)
            media_type = "Voice"

        await context.bot.send_message(
            chat_id=admin_id,
            text=f"Forwarded {media_type} from {sender_name} (chat ID: {source_id})"
        )
    except Exception as e:
        logger.exception(f"Exception while forwarding message: {e}")