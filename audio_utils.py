import os
import tempfile
import subprocess
import speech_recognition as sr
import whisper

recognizer = sr.Recognizer()
whisper_model = whisper.load_model("base")  # Or "small", "medium", depending on accuracy/speed

def extract_text_from_audio(audio_path: str) -> str:
    try:
        with sr.AudioFile(audio_path) as source:
            audio = recognizer.record(source)
        return recognizer.recognize_google(audio)
    except Exception as e:
        print(f"[SpeechRecognition] Error: {e}")
        return ""

def extract_text_from_video(video_path: str) -> str:
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
            audio_path = temp_audio.name

        # Use ffmpeg to extract audio from video
        subprocess.run([
            "ffmpeg", "-y", "-i", video_path,
            "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", audio_path
        ], check=True)

        # You can use Whisper or SpeechRecognition here. Let's use Whisper:
        result = whisper_model.transcribe(audio_path)
        os.remove(audio_path)
        return result["text"].strip()

    except Exception as e:
        print(f"[Video Transcription] Error: {e}")
        return ""
