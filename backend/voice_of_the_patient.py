import os
import logging
from io import BytesIO
from pydub import AudioSegment
from dotenv import load_dotenv

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
load_dotenv()

from groq import Groq


try:
    import speech_recognition as sr
except ImportError:
    sr = None

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def record_audio(file_path, timeout=20, phrase_time_limit=None):
    """
    Simplified function to record audio from the microphone and save it as an MP3 file.
    """
    if sr is None:
        logging.error("speech_recognition library is not installed or failed to import. Local audio recording is unavailable.")
        return

    recognizer = sr.Recognizer()
    
    try:
        with sr.Microphone() as source:
            logging.info("Adjusting for ambient noise...")
            recognizer.adjust_for_ambient_noise(source, duration=1)
            logging.info("Start speaking now...")
            
            # Record the audio
            audio_data = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
            logging.info("Recording complete.")
            
            # Convert the recorded audio to an MP3 file
            wav_data = audio_data.get_wav_data()
            audio_segment = AudioSegment.from_wav(BytesIO(wav_data))
            audio_segment.export(file_path, format="mp3", bitrate="128k")
            
            logging.info(f"Audio saved to {file_path}")

    except Exception as e:
        logging.error(f"An error occurred during local recording: {e}")


def transcribe_with_groq(stt_model="whisper-large-v3", audio_filepath=None, GROQ_API_KEY=None):
    """
    Transcribe audio file using Groq Whisper API.
    """
    if not audio_filepath or not os.path.exists(audio_filepath):
        return ""

    api_key = GROQ_API_KEY or os.environ.get("GROQ_API_KEY")
    if not api_key:
        load_dotenv(os.path.join(PROJECT_ROOT, ".env"), override=True)
        api_key = os.environ.get("GROQ_API_KEY")

    if not api_key:
        logging.warning("GROQ_API_KEY is not set. Cannot transcribe audio.")
        return "Audio provided, but GROQ_API_KEY is not configured."


    try:
        client = Groq(api_key=api_key)
        with open(audio_filepath, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model=stt_model or "whisper-large-v3",
                file=audio_file,
                language="en"
            )
        return transcription.text
    except Exception as e:
        logging.error(f"Error during audio transcription: {e}")
        return f"[Transcription error: {e}]"

