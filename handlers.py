import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from utils import is_homework, get_route_map, load_env

logger = logging.getLogger(__name__)

# In-memory dynamic route map
ROUTE_MAP = get_route_map()

def update_route_map(update, context):
    context.bot_data["ROUTE_MAP"] = ROUTE_MAP

# /id command: show the chat ID
async def chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    await update.message.reply_text(f" Chat ID: {chat.id}", parse_mode='Markdown')

# /start command: greet user
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f" /start from {user.username or user.id}")
    await update.message.reply_text(" Hello! I'm your Homework Forwarder Bot. Drop homework, and I will pass it along!")

# /status command: check health
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f" /status from {user.username or user.id}")
    
    status_msg = (
        " *Bot Status*\n"
        f" Uptime: always-on (webhook)\n"
        f" Active Routes: {len(ROUTE_MAP)} source-to-target mappings\n"
        f" Admin Chat ID: {context.bot_data.get('ADMIN_CHAT_ID')}"
    )

    await update.message.reply_text(status_msg, parse_mode="Markdown")

# /reload command: reload .env and route map
async def reload_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    admin_id = context.bot_data.get("ADMIN_CHAT_ID")

    if user.id != admin_id:
        await update.message.reply_text(" Access denied. Only the admin can reload config.")
        return

    try:
        load_env()
        global ROUTE_MAP
        ROUTE_MAP = get_route_map()
        context.bot_data["ROUTE_MAP"] = ROUTE_MAP
        logger.info(" Config and routes reloaded.")
        await update.message.reply_text(" Config reloaded. New routes applied.")
    except Exception as e:
        logger.exception(" Failed to reload config:")
        await update.message.reply_text(" Failed to reload config.")

# /addroutes command
async def add_routes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    admin_id = context.bot_data.get("ADMIN_CHAT_ID")

    if user.id != admin_id:
        await update.message.reply_text(" Access denied. Only the admin can add routes.")
        return

    global ROUTE_MAP
    new_routes = update.message.text.replace("/addroutes", "").strip()
    added = []
    for pair in new_routes.split(","):
        if ":" in pair:
            try:
                src, tgt = map(int, pair.strip().split(":"))
                ROUTE_MAP[src] = tgt
                added.append(f"{src} → {tgt}")
            except ValueError:
                continue

    context.bot_data["ROUTE_MAP"] = ROUTE_MAP
    if added:
        await update.message.reply_text(f"✅ Added {len(added)} route(s):\n" + "\n".join(added))
    else:
        await update.message.reply_text("❌ No valid routes added.")

# /removeroutes command
async def remove_routes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    admin_id = context.bot_data.get("ADMIN_CHAT_ID")

    if user.id != admin_id:
        await update.message.reply_text(" Access denied. Only the admin can remove routes.")
        return

    global ROUTE_MAP
    to_remove = update.message.text.replace("/removeroutes", "").strip()
    removed = []
    for src in to_remove.split(","):
        try:
            src_id = int(src.strip())
            if src_id in ROUTE_MAP:
                del ROUTE_MAP[src_id]
                removed.append(str(src_id))
        except ValueError:
            continue

    context.bot_data["ROUTE_MAP"] = ROUTE_MAP
    if removed:
        await update.message.reply_text(f"❌ Removed {len(removed)} route(s):\n" + "\n".join(removed))
    else:
        await update.message.reply_text("⚠️ No valid routes removed.")

# Main message forwarding logic
async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = update.message
        if not message:
            logger.warning(" No message found.")
            return

        route_map = context.bot_data.get("ROUTE_MAP", {})
        source_id = message.chat_id
        target_id = route_map.get(source_id)
        admin_id = context.bot_data.get("ADMIN_CHAT_ID")

        if not target_id:
            logger.warning(f" No target mapped for source chat ID: {source_id}")
            return

        if message.text and not is_homework(message):
            logger.info(f" Ignored non-homework message: {message.text}")
            return

        caption = message.caption or ""
        sender = update.effective_user
        sender_name = f"@{sender.username}" if sender.username else f"user {sender.id}"

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
        else:
            logger.warning(f" Unsupported message type: {message}")
            return

        logger.info(f" Forwarded {media_type} from {source_id} to {target_id}.")

        # Notify admin
        await context.bot.send_message(
            chat_id=admin_id,
            text=f" Forwarded {media_type} from {sender_name} (chat ID: {source_id})."
        )

    except Exception as e:
        logger.exception(f" Exception while forwarding message: {e}")