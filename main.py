from bot import start_bot
from handlers import register_handlers

def main():
    register_handlers()  # Register handlers
    start_bot()          # Start the bot and set the webhook

if __name__ == "__main__":
    main()
