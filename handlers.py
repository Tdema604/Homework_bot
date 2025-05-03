import logging
from telegram import Update
from telegram.ext import ContextTypes
from utils import is_homework, get_route_map, load_env, get_media_type_icon, escape_markdown

logger = logging.getLogger(__name__)
ROUTE_MAP = get_route_map()

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"📥 /start from {user.username or user.id}")
    await update.message.reply_text("👋 Hello! I'm your Homework Forwarder Bot. Drop homework, and I’ll pass it along!")

# /id command
async def chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    logger.info(f"📥 /id command from {update.effective_user.username or update.effective_user.id}")
    await update.message.reply_text(f"🆔 Chat ID: {chat.id}", parse_mode='Markdown')

# /status command
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"📥 /status from {user.username or user.id}")

    status_msg = (
        "✅ *Bot Status*\n"
        f"• Uptime: always-on (webhook)\n"
        f"• Active Routes: {len(ROUTE_MAP)} source-to-target mappings\n"
        f"• Admin Chat ID: {context.bot_data.get('ADMIN_CHAT_ID')}"
    )

    await update.message.reply_text(status_msg, parse_mode="Markdown")

# /reload command
async def reload_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    admin_id = context.bot_data.get("ADMIN_CHAT_ID")

    if user.id != admin_id:
        logger.warning(f"⛔️ Unauthorized access attempt for /reload by {user.username or user.id}")
        await update.message.reply_text("⛔️ Access denied. Only the admin can reload config.")
        return

    try:
        load_env()
        global ROUTE_MAP
        ROUTE_MAP = get_route_map()
        logger.info("♻️ Config and routes reloaded successfully.")
        await update.message.reply_text("♻️ Config reloaded. New routes applied.")
    except Exception as e:
        logger.exception("🚨 Failed to reload config:")
        await update.message.reply_text("❌ Failed to reload config.")

# Main message forwarding logic
async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = update.message
        if not message:
            logger.warning("⚠️ No message found in the update.")
            return

        source_id = message.chat_id
        target_id = context.bot_data["ROUTE_MAP"].get(source_id)
        admin_id = context.bot_data.get("ADMIN_CHAT_ID")

        if not target_id:
            logger.warning(f"⛔️ No target mapped for source chat ID: {source_id}")
            return

        if message.text and not is_homework(message):
            logger.info(f"🚫 Ignored non-homework message from {source_id}: {message.text}")
            return

        caption = escape_markdown(message.caption or "")
        sender = update.effective_user
        sender_name_raw = f"@{sender.username}" if sender.username else f"user {sender.id}"
        sender_name = escape_markdown(sender_name_raw)


        media_type = None

        if message.text:
            text = escape_markdown(message.text)
            await context.bot.send_message(chat_id=target_id, text=caption + text, parse_mode="MarkdownV2")
            media_type = "Text"
        elif message.photo:
            await context.bot.send_photo(chat_id=target_id, photo=message.photo[-1].file_id, caption=caption, parse_mode="MarkdownV2")
            media_type = "Photo"
        elif message.video:
            await context.bot.send_video(chat_id=target_id, video=message.video.file_id, caption=caption, parse_mode="MarkdownV2")
            media_type = "Video"
        elif message.document:
            await context.bot.send_document(chat_id=target_id, document=message.document.file_id, caption=caption, parse_mode="MarkdownV2")
            media_type = "Document"
        elif message.audio:
            await context.bot.send_audio(chat_id=target_id, audio=message.audio.file_id, caption=caption, parse_mode="MarkdownV2")
            media_type = "Audio"
        elif message.voice:
            await context.bot.send_voice(chat_id=target_id, voice=message.voice.file_id)
            media_type = "Voice"
        else:
            logger.warning(f"⚠️ Unsupported message type from {source_id}: {message}")
            return

        logger.info(f"✅ Forwarded {media_type} from {source_id} to {target_id}.")

        # Admin notification
        if admin_id:
            await context.bot.send_message(
                chat_id=admin_id,
                text=escape_markdown(f"📫 Forwarded *{media_type}* from {sender_name} (chat ID: {source_id})"),
                parse_mode="MarkdownV2"
            )

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"🚨 Exception while forwarding message:\n{error_details}")

        if context.bot_data.get("ADMIN_CHAT_ID"):
            await context.bot.send_message(
                chat_id=context.bot_data["ADMIN_CHAT_ID"],
                text=escape_markdown(f"📫 Forwarded *{media_type}* from {sender_name} (chat ID: {source_id})"),
                parse_mode="MarkdownV2"
            )
