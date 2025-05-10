import datetime
import pytz
import os
from telegram import Update
from datetime import datetime
from telegram import Update, MessageEntity
from telegram.ext import CommandHandler, MessageHandler, filters, ContextTypes
from utils import (
    is_admin,
    is_junk_message,
    get_target_chat_id,
    extract_text_from_image,
    transcribe_audio_with_whisper,
    is_homework_text,
    forward_homework,
    get_weekly_summary,
    clear_homework_log,
    track_sender_activity,
    list_sender_activity,
    clear_sender_data,
    parse_routes_map,
    add_route_to_env,
    delete_route_from_env,
)

# ========================= Admin Commands =========================
def get_dynamic_greeting():
    bhutan_tz = pytz.timezone("Asia/Thimphu")  # Bhutan timezone
    current_time = datetime.now(bhutan_tz)
    hour = current_time.hour

    if 5 <= hour < 12:
        return "Good morning"
    elif 12 <= hour < 17:
        return "Good afternoon"
    elif 17 <= hour < 22:
        return "Good evening"
    else:
        return "Good night"

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    greeting = get_dynamic_greeting()
    welcome_text = f"{greeting}, {user_name}! Welcome to the Homework Forwarder Bot 🎓.\n\nUse /help to get more details about the available commands."

    await update.message.reply_text(welcome_text)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    await update.message.reply_text("✅ Bot is up and running!")

async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🆔 Your chat ID is: `{update.effective_chat.id}`", parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_help = (
        "**👩‍🏫 User Commands:**\n"
        "/id - Show your chat ID\n"
        "/feedback - Send feedback to the bot admin\n"
    )

    admin_help = (
        "\n**🛠️ Admin Commands:**\n"
        "/status - Check bot status\n"
        "/help - Show this help menu\n"
        "/list_routes - List all current group routes\n"
        "/add_route <from_id> <to_id> - Add a new route\n"
        "/delete_route <from_id> - Delete a route\n"
        "/reload_config - Reload route config\n"
        "/weekly_summary - Get summary of homework forwarded\n"
        "/clear_homework_log - Clear forwarded homework log\n"
        "/list_senders - Show sender activity log\n"
        "/clear_senders - Clear sender activity log"
    )

    await update.message.reply_text(user_help + admin_help, parse_mode="Markdown")

async def list_routes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    routes = context.bot_data.get("ROUTES_MAP", {})
    if not routes:
        await update.message.reply_text("❌ No routes found.")
        return
    msg = "📚 Current Routes:\n"
    for src, dst in routes.items():
        msg += f"{src} ➜ {dst}\n"
    await update.message.reply_text(msg)


async def add_routes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    try:
        src = int(context.args[0])
        dst = int(context.args[1])
        routes = context.bot_data.get("ROUTES_MAP", {})
        routes[src] = dst
        context.bot_data["ROUTES_MAP"] = routes
        await update.message.reply_text(f"✅ Route added: {src} ➜ {dst}")
        add_route_to_env(src, dst)
    except Exception as e:
        await update.message.reply_text(f"❌ Error adding route: {e}")


async def delete_routes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    try:
        src = int(context.args[0])
        routes = context.bot_data.get("ROUTES_MAP", {})
        if src in routes:
            del routes[src]
            context.bot_data["ROUTES_MAP"] = routes
            delete_route_from_env(src)
            await update.message.reply_text(f"🗑️ Route deleted: {src}")
        else:
            await update.message.reply_text("⚠️ Route not found.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error deleting route: {e}")

async def reload_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    try:
        context.bot_data["ROUTES_MAP"] = parse_routes_map(os.getenv("ROUTES_MAP", ""))
        await update.message.reply_text("✅ Configuration reloaded.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def get_weekly_summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    summary = get_weekly_summary(context)
    await update.message.reply_text(summary or "📭 No homework forwarded this week.")

async def clear_homework_log_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    clear_homework_log(context)
    await update.message.reply_text("🧹 Cleared homework log!")


async def list_senders_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    await update.message.reply_text(list_sender_activities(context))


async def clear_senders_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    clear_sender_data(context)
    await update.message.reply_text("🧼 Cleared sender activity log.")


# ========================= Feedback =========================

async def feedback_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📝 Please reply to this message with your feedback.")
    return


# ========================= Message Handlers =========================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = message.chat_id
    routes = context.bot_data.get("ROUTES_MAP", {})

    # Junk filtering
    if message.text and any(entity.type == MessageEntity.BOT_COMMAND for entity in message.entities or []):
        if "@" in message.text:
            return

    # Track sender
    track_sender_activity(update, context)

    # Check and forward text messages
    if message.text and is_homework_message(message.text):
        await forward_homework(context, message, routes)
        return

    # If image with caption
    if message.photo:
        caption = message.caption or ""
        if is_homework_message(caption):
            await forward_homework(context, message, routes)
            return
        # OCR from image
        photo_file = await message.photo[-1].get_file()
        image_path = await photo_file.download_to_drive()
        extracted_text = extract_text_from_image(image_path)
        if is_homework_message(extracted_text):
            await forward_homework(context, message, routes)
            return

    # If voice or audio or video message
    if message.voice or message.audio or message.video_note:
        transcript = await transcribe_audio_message(message, context)
        if transcript and is_homework_message(transcript):
            await forward_homework(context, message, routes)
            return

# ========================= Handler Registration =========================
def register_handlers(application):
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("id", id_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("list_routes", list_routes_command))
    application.add_handler(CommandHandler("add_route", add_route_command))
    application.add_handler(CommandHandler("delete_routes", delete_routes_command))
    application.add_handler(CommandHandler("reload_config", reload_config, filters=filters.User(ADMIN_CHAT_IDS)))
    application.add_handler(CommandHandler("get_weekly_summary", get_weekly_summary_command))
    application.add_handler(CommandHandler("clear_homework_log", clear_homework_log_command))
    application.add_handler(CommandHandler("list_senders", list_senders_command))
    application.add_handler(CommandHandler("clear_senders", clear_senders_command))
    application.add_handler(CommandHandler("feedback", feedback_command))
    application.add_handler(MessageHandler(filters.ALL, handle_message))

