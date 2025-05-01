async def forward_message(update: Update, context: CallbackContext):
    try:
        message = update.message
        if not message:
            logger.warning("No message found in update!")
            return

        source_id = context.bot_data["SOURCE_CHAT_ID"]
        target_id = context.bot_data["TARGET_CHAT_ID"]
        admin_id = context.bot_data["ADMIN_CHAT_ID"]

        # 🚫 Ignore messages NOT from the student group
        if message.chat.id != source_id:
            logger.info(f"Ignored message from non-source chat: {message.chat.id}")
            return

        # 🚫 Ignore bot's own messages (avoid feedback loop)
        if message.from_user and message.from_user.is_bot:
            logger.info("Ignored bot's own message.")
            return

        # ✅ Optional: only forward if message *looks like* homework
        if message.text:
            lowered = message.text.lower()
            if not any(keyword in lowered for keyword in ["homework", "hw", "assignment", "chapter", "exercise", "math", "science", "workbook"]):
                logger.info(f"Ignored non-homework text: {message.text}")
                return

        # 📨 Forward message based on media type
        if message.text:
            media_type = "Text"
            await context.bot.send_message(chat_id=target_id, text=message.text)
        elif message.photo:
            media_type = "Photo"
            await context.bot.send_photo(chat_id=target_id, photo=message.photo[-1].file_id)
        elif message.video:
            media_type = "Video"
            await context.bot.send_video(chat_id=target_id, video=message.video.file_id)
        elif message.document:
            media_type = "Document"
            await context.bot.send_document(chat_id=target_id, document=message.document.file_id)
        elif message.audio:
            media_type = "Audio"
            await context.bot.send_audio(chat_id=target_id, audio=message.audio.file_id)
        elif message.voice:
            media_type = "Voice"
            await context.bot.send_voice(chat_id=target_id, voice=message.voice.file_id)
        else:
            logger.warning(f"Unsupported media type: {message}")
            return

        # ✅ Admin notification
        user = update.effective_user
        logger.info(f"✅ Forwarded {media_type} from {user.id}")
        await context.bot.send_message(
            chat_id=admin_id,
            text=f"✅ Message forwarded from @{user.username or user.id} ({media_type})."
        )

    except Exception as e:
        logger.error(f"🔥 Error forwarding message: {e}")
