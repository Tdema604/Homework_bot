import speech_recognition as sr
from pydub import AudioSegment

# STEP 1: Convert .ogg to .wav using pydub + ffmpeg
def convert_ogg_to_wav(input_path, output_path):
    audio = AudioSegment.from_file(input_path, format="ogg")
    audio.export(audio_2025_05_08_16-12-15.ogg, format="wav")

# STEP 2: Transcribe .wav to text
def transcribe_wav(wav_path):
    recognizer = sr.Recognizer()
    with sr.AudioFile(wav_path) as source:
        audio_data = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio_data)
            print("Transcription:", text)
        except sr.UnknownValueError:
            print("Could not understand audio.")
        except sr.RequestError as e:
            print(f"API error: {e}")

# Test with a sample .ogg file
ogg_file = "voice.ogg"         # Replace with your file
wav_file = "converted.wav"

convert_ogg_to_wav(ogg_file, wav_file)
transcribe_wav(wav_file)
