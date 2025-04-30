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
