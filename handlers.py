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

# /listroutes command
async def list_routes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"📥 /listroutes from {user.username or user.id}")

    routes = context.bot_data.get("ROUTE_MAP", {})
    if not routes:
        await update.message.reply_text("⚠️ No routes configured yet.")
        return

    msg = "*📚 Active Routes:*\n"
    for source, target in routes.items():
        msg += f"• `{source}` ➡️ `{target}`\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

# /addroute command
async def add_route(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"📥 /addroute from {user.username or user.id}")
    admin_id = context.bot_data.get("ADMIN_CHAT_ID")

    if user.id != admin_id:
        logger.warning(f"⛔️ Unauthorized attempt to add route by {user.username or user.id}")
        await update.message.reply_text("⛔️ Only the admin can add routes.")
        return

    if len(context.args) < 2:
        await update.message.reply_text("❗ Usage: `/addroute <source_id> <target_id>`", parse_mode="Markdown")
        return

    try:
        source_id, target_id = map(int, context.args)
        context.bot_data["ROUTE_MAP"][source_id] = target_id
        logger.info(f"✅ Route added: {source_id} ➡️ {target_id}")
        await update.message.reply_text(f"✅ Route added: `{source_id}` ➡️ `{target_id}`", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"🚫 Error adding route: {e}")
        await update.message.reply_text("❗ Error processing the request. Please try again.", parse_mode="Markdown")

# /removeroute command
async def remove_route(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"📥 /removeroute from {user.username or user.id}")
    admin_id = context.bot_data.get("ADMIN_CHAT_ID")

    if user.id != admin_id:
        logger.warning(f"⛔️ Unauthorized attempt to remove route by {user.username or user.id}")
        await update.message.reply_text("⛔️ Only the admin can remove routes.")
        return

    if len(context.args) < 1:
        await update.message.reply_text("❗ Usage: `/removeroute <source_id>`", parse_mode="Markdown")
        return

    try:
        source_id = int(context.args[0])
        if source_id in context.bot_data["ROUTE_MAP"]:
            del context.bot_data["ROUTE_MAP"][source_id]
            logger.info(f"🗑️ Route removed for source ID {source_id}")
            await update.message.reply_text(f"🗑️ Route removed for `{source_id}`", parse_mode="Markdown")
        else:
            await update.message.reply_text("⚠️ No route found for that source ID.")
    except Exception as e:
        logger.error(f"🚫 Error removing route: {e}")
        await update.message.reply_text("❗ Error processing the request. Please try again.", parse_mode="Markdown")

# Message forwarder
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
            await context.bot.send_message(chat_id=target_id, text=text, parse_mode="MarkdownV2")
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

        # Short preview for admin notification
        preview_raw = message.caption if message.caption else (message.text or "")
        preview = escape_markdown(preview_raw[:100])
        media_icon = escape_markdown(get_media_type_icon(message))
        safe_source_id = escape_markdown(str(source_id))

        await context.bot.send_message(
            chat_id=admin_id,
            text=(
                f"{media_icon} Forwarded *{media_type}* from {sender_name} \chat ID: `{safe_source_id}`\\n"
                f"📝 \"{preview}\""
            ),
            parse_mode="MarkdownV2"
        )

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"🚨 Exception while forwarding message:\n{error_details}")
        if context.bot_data.get("ADMIN_CHAT_ID"):
            await context.bot.send_message(
                chat_id=context.bot_data["ADMIN_CHAT_ID"],
                text=f"❌ Error occurred during forwarding. Check logs for details.\nError Details: ```{escape_markdown(error_details)}```",
                parse_mode="MarkdownV2"
            )
