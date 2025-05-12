import logging
from telegram import Update
from telegram.ext import CommandHandler, MessageHandler, Filters, CallbackContext
from utils import is_admin, is_homework_text, is_junk_message, extract_text_from_image, transcribe_audio
from datetime import datetime

logger = logging.getLogger(__name__)

# Dynamic Greetings
def get_dynamic_greeting() -> str:
    now = datetime.now()
    current_hour = now.hour
    current_minute = now.minute
    # Determine greeting based on time
    if 6 <= current_hour < 12:
        return f"Good morning! ({current_hour}:{current_minute})"
    elif 12 <= current_hour < 18:
        return f"Good afternoon! ({current_hour}:{current_minute})"
    elif 18 <= current_hour < 22:
        return f"Good evening! ({current_hour}:{current_minute})"
    else:
        return f"Good night! ({current_hour}:{current_minute})"

# Command Handlers
async def start(update: Update, context: CallbackContext) -> None:
    greeting = get_dynamic_greeting()
    await update.message.reply_text(f"{greeting}\nWelcome to the Homework Forwarding Bot!")

async def help_command(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    help_text = """
    Here are the commands you can use:
    
    /start - Start the bot with a dynamic greeting
    /status - Check bot status and webhook URL
    /id - Get your Telegram ID
    /help - Get a list of available commands
    """
    if is_admin(user.id):  # Admin-only commands
        help_text += """
        /list_senders - View sender activity logs
        /delete_senders - Delete sender activity logs
        /list_routes - View the current route list
        /add_routes - Add a new route
        /delete_routes - Delete an existing route
        /weekly_summary - View the weekly homework summary
        /clear_homework_log - Clear the homework log
        """
    await update.message.reply_text(help_text)

async def status(update: Update, context: CallbackContext) -> None:
    webhook_url = context.bot.get_webhook_url()
    await update.message.reply_text(f"Bot is live and running!\nWebhook URL: {webhook_url}")

async def get_id(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    await update.message.reply_text(f"Your Telegram ID: {user.id}")

# Admin command to list senders' activity
async def list_senders(update: Update, context: CallbackContext) -> None:
    if not is_admin(update.message.from_user.id):
        await update.message.reply_text("You are not authorized to use this command.")
        return
    # Assuming bot_data["senders_activity"] contains a log of sender activities
    senders_activity = bot_data.get("senders_activity", [])
    activity_text = "\n".join([f"{activity['name']} ({activity['id']}): {activity['last_message']}" for activity in senders_activity])
    await update.message.reply_text(f"Sender Activity Logs:\n{activity_text or 'No activity recorded.'}")

# Admin command to delete sender activity
async def delete_sender_activity(update: Update, context: CallbackContext) -> None:
    if not is_admin(update.message.from_user.id):
        await update.message.reply_text("You are not authorized to use this command.")
        return
    bot_data["senders_activity"] = []
    await update.message.reply_text("Sender activity logs have been cleared.")

# Admin command to list routes
async def list_routes(update: Update, context: CallbackContext) -> None:
    if not is_admin(update.message.from_user.id):
        await update.message.reply_text("You are not authorized to use this command.")
        return
    routes = os.getenv("ROUTES_MAP")  # or bot_data["routes"]
    await update.message.reply_text(f"Current routes: {routes}")

# Admin command to add a route
async def add_route(update: Update, context: CallbackContext) -> None:
    if not is_admin(update.message.from_user.id):
        await update.message.reply_text("You are not authorized to use this command.")
        return
    # Add logic for adding a new route, based on user's input
    new_route = context.args
    if new_route:
        # Assuming bot_data["routes"] is a list
        bot_data["routes"].append(new_route)
        await update.message.reply_text(f"Route {new_route} added successfully.")
    else:
        await update.message.reply_text("Please provide the route to add.")

# Admin command to delete a route
async def delete_route(update: Update, context: CallbackContext) -> None:
    if not is_admin(update.message.from_user.id):
        await update.message.reply_text("You are not authorized to use this command.")
        return
    route_to_delete = context.args[0] if context.args else None
    if route_to_delete:
        # Assuming bot_data["routes"] is a list
        bot_data["routes"] = [route for route in bot_data["routes"] if route != route_to_delete]
        await update.message.reply_text(f"Route {route_to_delete} deleted successfully.")
    else:
        await update.message.reply_text("Please provide the route to delete.")

# Admin command to get weekly homework summary
async def weekly_summary(update: Update, context: CallbackContext) -> None:
    if not is_admin(update.message.from_user.id):
        await update.message.reply_text("You are not authorized to use this command.")
        return
    # Assuming homework log is stored in bot_data["homework_log"]
    homework_summary = bot_data.get("homework_log", [])
    summary_text = "\n".join([f"Week {i+1}: {log['summary']}" for i, log in enumerate(homework_summary)])
    await update.message.reply_text(f"Weekly Homework Summary:\n{summary_text or 'No summary available.'}")

# Admin command to clear homework log
async def clear_homework_log(update: Update, context: CallbackContext) -> None:
    if not is_admin(update.message.from_user.id):
        await update.message.reply_text("You are not authorized to use this command.")
        return
    bot_data["homework_log"] = []
    await update.message.reply_text("Homework log cleared.")

# Forward homework messages (text, image, audio, video)
async def forward_homework(update: Update, context: CallbackContext) -> None:
    message = update.message
    if is_junk_message(message.text):
        return  # Ignore junk messages
    
    if is_homework_text(message.text):
        # Forward message if homework-related
        target_group_id = bot_data["routes"].get(message.chat.id)
        if target_group_id:
            await context.bot.send_message(target_group_id, message.text)
        else:
            await update.message.reply_text("No route defined for this class.")

# Main function to add all handlers
def main():
    from telegram.ext import Application
    application = Application.builder().token("YOUR_BOT_API_KEY").build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("id", get_id))
    application.add_handler(CommandHandler("list_senders", list_senders))
    application.add_handler(CommandHandler("delete_senders", delete_sender_activity))
    application.add_handler(CommandHandler("list_routes", list_routes))
    application.add_handler(CommandHandler("add_routes", add_route))
    application.add_handler(CommandHandler("delete_routes", delete_route))
    application.add_handler(CommandHandler("weekly_summary", weekly_summary))
    application.add_handler(CommandHandler("clear_homework_log", clear_homework_log))

    # Forward homework logic
    application.add_handler(MessageHandler(Filters.text & ~Filters.command, forward_homework))
    application.add_handler(MessageHandler(Filters.photo, forward_homework))
    application.add_handler(MessageHandler(Filters.audio, forward_homework))
    application.add_handler(MessageHandler(Filters.video, forward_homework))

    application.run_polling()

if __name__ == '__main__':
    main()
