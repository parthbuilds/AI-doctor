import os
import platform
import logging
from dotenv import load_dotenv

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
load_dotenv()

from gtts import gTTS
import elevenlabs
from elevenlabs.client import ElevenLabs

from elevenlabs.core.api_error import ApiError
from pydub import AudioSegment, effects

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def _play_audio_locally(output_filepath):
    """Optionally play audio locally on host machine if desktop environment."""
    if os.environ.get("VERCEL") or os.environ.get("DISABLE_LOCAL_PLAYBACK"):
        return
    # In web app mode, we don't need to block on host speaker playback, but if desired:
    try:
        os_name = platform.system()
        if os_name == "Darwin":  # macOS
            # non-blocking playback or pass to avoid audio collisions
            pass
        elif os_name == "Windows":
            pass
        elif os_name == "Linux":
            pass
    except Exception as e:
        logging.debug(f"Local audio playback skipped: {e}")


def text_to_speech_with_gtts(input_text, output_filepath, speed: float = 1.0):
    """
    Generate speech from text using Google Text-to-Speech (gTTS).
    Always returns the output filepath if successful, or None if failed/empty.
    """
    if not input_text or not input_text.strip():
        return None

    # Sanitize input text: remove markdown formatting for cleaner speech
    clean_text = input_text.replace("*", "").replace("#", "").replace("-", " ")

    try:
        os.makedirs(os.path.dirname(os.path.abspath(output_filepath)), exist_ok=True)
        audioobj = gTTS(
            text=clean_text,
            lang="en",
            slow=False
        )
        audioobj.save(output_filepath)
        
        if speed and speed != 1.0:
            try:
                segment = AudioSegment.from_file(output_filepath)
                faster = effects.speedup(segment, playback_speed=speed)
                faster.export(output_filepath, format="mp3")
            except Exception as e:
                logging.warning(f"Could not adjust audio speed: {e}")
                
        _play_audio_locally(output_filepath)
        return output_filepath
    except Exception as e:
        logging.error(f"gTTS error: {e}")
        return None


def text_to_speech_with_elevenlabs(input_text, output_filepath, speed: float = 1.0):
    """
    Generate speech using ElevenLabs API, falling back to gTTS if unavailable.
    """
    if not input_text or not input_text.strip():
        return None

    eleven_key = os.environ.get("ELEVEN_API_KEY") or os.environ.get("ELEVENLABS_API_KEY")
    if not eleven_key:
        return text_to_speech_with_gtts(input_text=input_text, output_filepath=output_filepath, speed=speed)

    try:
        os.makedirs(os.path.dirname(os.path.abspath(output_filepath)), exist_ok=True)
        client = ElevenLabs(api_key=eleven_key)
        
        # Clean text
        clean_text = input_text.replace("*", "").replace("#", "").replace("-", " ")
        audio_stream = client.text_to_speech.convert(
            voice_id="JBFqnCBsd6RMkjVDRZzb",
            text=clean_text,
            model_id="eleven_multilingual_v2"
        )
        
        with open(output_filepath, "wb") as f:
            for chunk in audio_stream:
                f.write(chunk)
        
        if speed and speed != 1.0:
            try:
                segment = AudioSegment.from_file(output_filepath)
                faster = effects.speedup(segment, playback_speed=speed)
                faster.export(output_filepath, format="mp3")
            except Exception as e:
                logging.warning(f"Could not adjust audio speed: {e}")
                
        _play_audio_locally(output_filepath)
        return output_filepath
    except (ApiError, Exception) as e:
        logging.warning(f"ElevenLabs failed ({e}), falling back to gTTS.")
        return text_to_speech_with_gtts(input_text=input_text, output_filepath=output_filepath, speed=speed)