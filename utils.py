import os
import logging
import tempfile
from typing import Optional
from PIL import Image
import pytesseract
from pydub import AudioSegment
import moviepy.editor as mp

from telegram import Message, InputFile
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)
TESSDATA_PREFIX = os.getenv("TESSDATA_PREFIX", "./tessdata")
faster_whisper_model = None  # lazy-loaded model

# --- OCR ---
def extract_text_from_image(file_path: str) -> str:
    """Run OCR on image file using pytesseract (supports Dzongkha if available)."""
    try:
        image = Image.open(file_path)
        return pytesseract.image_to_string(image, lang="dzo+eng").strip()
    except Exception as e:
        logger.error(f"OCR failed: {e}")
        return ""

async def setup_dzongkha_ocr():
    """Ensure Dzongkha language support is available (asynchronously)."""
    try:
        dzo_path = os.path.join(TESSDATA_PREFIX, "dzo.traineddata")
        if not os.path.exists(dzo_path):
            os.makedirs(TESSDATA_PREFIX, exist_ok=True)
            import aiohttp
            url = "https://github.com/tesseract-ocr/tessdata/raw/main/dzo.traineddata"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        with open(dzo_path, "wb") as f:
                            f.write(await resp.read())
    except Exception as e:
        logger.error(f"Failed to set up Dzongkha OCR: {e}")

# --- Audio Transcription ---
def lazy_load_faster_whisper():
    global faster_whisper_model
    if faster_whisper_model is None:
        from faster_whisper import WhisperModel
        faster_whisper_model = WhisperModel("tiny", compute_type="int8")
    return faster_whisper_model

def transcribe_audio(file_path: str) -> str:
    """Convert audio file to text using faster-whisper (tiny model)."""
    try:
        model = lazy_load_faster_whisper()
        segments, _ = model.transcribe(file_path)
        return " ".join([seg.text.strip() for seg in segments if seg.text]).strip()
    except Exception as e:
        logger.error(f"Audio transcription failed: {e}")
        return ""

def convert_voice_to_wav(voice_bytes: bytes) -> str:
    """Convert Telegram voice message bytes (OGG/MP3) to WAV for transcription."""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as out_file:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as tmp_ogg:
                tmp_ogg.write(voice_bytes)
                tmp_ogg.flush()
                audio = AudioSegment.from_file(tmp_ogg.name)
                audio.export(out_file.name, format="wav")
            return out_file.name
    except Exception as e:
        logger.error(f"Failed to convert voice to WAV: {e}")
        return ""

def convert_video_to_wav(video_path: str) -> str:
    """Extract audio from video as WAV."""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as wav_file:
            video = mp.VideoFileClip(video_path)
            video.audio.write_audiofile(wav_file.name, codec='pcm_s16le')
            return wav_file.name
    except Exception as e:
        logger.error(f"Failed to extract audio from video: {e}")
        return ""

# --- Message Filtering ---
def is_junk_message(text: Optional[str]) -> bool:
    """Detect junk/bot promotion messages."""
    if not text:
        return False
    junk_keywords = ["/nayavpn", "promo", "cheap price", "@", "join fast", "discount"]
    return any(junk in text.lower() for junk in junk_keywords)

def is_homework_text(text: str) -> bool:
    """Keyword-based heuristic to determine if message is homework-related."""
    keywords = ["homework", "classwork", "assignment", "exercise", "page", "question", "write", "draw"]
    return any(word in text.lower() for word in keywords)

# --- Forwarding ---
async def forward_message_to_parent_group(
    context: ContextTypes.DEFAULT_TYPE,
    message: Message,
    target_chat_id: int,
) -> None:
    """Forward or copy supported message types from student to parent group."""
    try:
        if message.text:
            await context.bot.send_message(chat_id=target_chat_id, text=message.text)
        elif message.photo:
            file_id = message.photo[-1].file_id
            caption = message.caption or ""
            await context.bot.send_photo(chat_id=target_chat_id, photo=file_id, caption=caption)
        elif message.document:
            await context.bot.send_document(chat_id=target_chat_id, document=message.document.file_id, caption=message.caption or "")
        elif message.audio:
            await context.bot.send_audio(chat_id=target_chat_id, audio=message.audio.file_id, caption=message.caption or "")
        elif message.voice:
            await context.bot.send_voice(chat_id=target_chat_id, voice=message.voice.file_id, caption=message.caption or "")
        elif message.video:
            await context.bot.send_video(chat_id=target_chat_id, video=message.video.file_id, caption=message.caption or "")
        else:
            await context.bot.send_message(chat_id=target_chat_id, text="[Unsupported message type]")
    except Exception as e:
        logger.error(f"Failed to forward message: {e}")
