# utils.py

async def forward_homework(bot, message, target_chat_id):
    try:
        await bot.forward_message(
            chat_id=target_chat_id,
            from_chat_id=message.chat_id,
            message_id=message.message_id,
        )
    except Exception as e:
        print(f"❌ Failed to forward message: {e}")

# Define is_spam function
def is_spam(message):
    # Simple spam detection logic (this is just an example)
    spam_keywords = ['free', 'win', 'prize', 'lottery', 'cash']
    
    # Check if any of the spam keywords are in the message
    if any(keyword in message.text.lower() for keyword in spam_keywords):
        return True
    return False
