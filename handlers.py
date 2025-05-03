Handlers.py
import logging
from telegram import Update
from telegram.ext import ContextTypes
from utils import is_homework, get_route_map

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! I'm your Homework Forwarder Bot.\nUse /status to check my current config.")

async def chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Chat ID: {update.effective_chat.id}", parse_mode="Markdown")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = context.bot_data.get("ADMIN_CHAT_ID")
    route_map = context.bot_data.get("ROUTE_MAP", {})
    allowed = context.bot_data.get("ALLOWED_SOURCE_CHAT_IDS", [])
    status_text = (
        f"Admin ID: {admin_id}\n"
        f"Allowed Sources: {allowed}\n"
        f"Active Routes: {len(route_map)}\n\n"
        + "\n".join([f"{k} → {v}" for k, v in route_map.items()])
    )
    await update.message.reply_text(status_text)

async def reload_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.bot_data["ROUTE_MAP"] = get_route_map()
    await update.message.reply_text("ROUTE_MAP reloaded from .env!")

async def add_route(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        return await update.message.reply_text("Usage: /addroute <source_chat_id> <target_chat_id>")

    try:
        source = int(context.args[0])
        target = int(context.args[1])
        context.bot_data.setdefault("ROUTE_MAP", {})[source] = target
        await update.message.reply_text(f"✅ Route added: {source} → {target}")
    except ValueError:
        await update.message.reply_text("Invalid chat IDs. They must be integers.")

async def remove_route(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        return await update.message.reply_text("Usage: /removeroute <source_chat_id>")

    try:
        source = int(context.args[0])
        if context.bot_data.get("ROUTE_MAP", {}).pop(source, None) is not None:
            await update.message.reply_text(f"❌ Route removed for source: {source}")
        else:
            await update.message.reply_text(f"No route found for source: {source}")
    except ValueError:
        await update.message.reply_text("Invalid chat ID.")

async def list_routes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    route_map = context.bot_data.get("ROUTE_MAP", {})
    if not route_map:
        await update.message.reply_text("No routes configured.")
    else:
        msg = "\n".join([f"{src} → {dst}" for src, dst in route_map.items()])
        await update.message.reply_text(f"Active Routes:\n{msg}")

async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    route_map = context.bot_data.get("ROUTE_MAP", {})
    admin_id = context.bot_data.get("ADMIN_CHAT_ID", None)
    allowed_sources = context.bot_data.get("ALLOWED_SOURCE_CHAT_IDS", [])

    source_id = update.effective_chat.id
    if source_id not in allowed_sources:
        logger.warning(f"Message from unallowed chat ID: {source_id}")
        return

    if not is_homework(message):
        logger.info(f"Ignored non-homework message from {source_id}")
        try:
            await message.delete()
            if admin_id:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=f"Spam or irrelevant content deleted from {source_id}."
                )
        except Exception as e:
            logger.warning(f"Failed to delete or notify about spam: {e}")
        return

    target_id = route_map.get(source_id)
    if not target_id:
        logger.warning(f"No route mapped for source: {source_id}")
        return

try:
        await message.forward(chat_id=target_id)
        logger.info(f"Forwarded from {source_id} to {target_id}")
        if admin_id:
            await context.bot.send_message(
                chat_id=admin_id,
                text=f"✅ Homework forwarded from {source_id} to {target_id}."
            )
    except Exception as e:
        logger.error(f"Failed to forward message: {e}")
        if admin_id:
            await context.bot.send_message(
                chat_id=admin_id,
                text=f"❌ Failed to forward message from {source_id} to {target_id}.\nError: {e}"
            )