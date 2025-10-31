import os
import subprocess
import platform
from gtts import gTTS
import elevenlabs
from elevenlabs.client import ElevenLabs
from elevenlabs.core.api_error import ApiError
from pydub import AudioSegment, effects

ELEVENLABS_API_KEY = os.environ.get("ELEVEN_API_KEY")

def text_to_speech_with_gtts(input_text, output_filepath, speed: float = 1.0):
    language="en"

    audioobj= gTTS(
        text=input_text,
        lang=language,
        slow=False
    )
    audioobj.save(output_filepath)
    if speed and speed != 1.0:
        try:
            segment = AudioSegment.from_file(output_filepath)
            faster = effects.speedup(segment, playback_speed=speed)
            faster.export(output_filepath, format="mp3")
        except Exception:
            pass
    os_name = platform.system()
    try:
        if os_name == "Darwin":  # macOS
            subprocess.run(['afplay', output_filepath])
        elif os_name == "Windows":  # Windows
            subprocess.run(['powershell', '-c', f'(New-Object Media.SoundPlayer "{output_filepath}").PlaySync();'])
        elif os_name == "Linux":  # Linux
            subprocess.run(['aplay', output_filepath])  # Alternative: use 'mpg123' or 'ffplay'
        else:
            raise OSError("Unsupported operating system")
    except Exception as e:
        print(f"An error occurred while trying to play the audio: {e}")


if __name__ == "__main__":
    pass


def text_to_speech_with_elevenlabs(input_text, output_filepath, speed: float = 1.0):
    if not ELEVENLABS_API_KEY:
        # Fallback immediately to gTTS if no API key
        return text_to_speech_with_gtts(input_text=input_text, output_filepath=output_filepath, speed=speed)

    try:
        client=ElevenLabs(api_key=ELEVENLABS_API_KEY)
        audio=client.generate(
            text= input_text,
            voice= "Aria",
            output_format= "mp3_22050_32",
            model= "eleven_turbo_v2"
        )
        elevenlabs.save(audio, output_filepath)
        if speed and speed != 1.0:
            try:
                segment = AudioSegment.from_file(output_filepath)
                faster = effects.speedup(segment, playback_speed=speed)
                faster.export(output_filepath, format="mp3")
            except Exception:
                pass
    except ApiError as e:
        # Permission or auth issues -> fallback to gTTS
        return text_to_speech_with_gtts(input_text=input_text, output_filepath=output_filepath, speed=speed)
    except Exception:
        # Any other error -> fallback to gTTS
        return text_to_speech_with_gtts(input_text=input_text, output_filepath=output_filepath, speed=speed)
    os_name = platform.system()
    try:
        if os_name == "Darwin":  # macOS
            subprocess.run(['afplay', output_filepath])
        elif os_name == "Windows":  # Windows
            subprocess.run(['powershell', '-c', f'(New-Object Media.SoundPlayer "{output_filepath}").PlaySync();'])
        elif os_name == "Linux":  # Linux
            subprocess.run(['aplay', output_filepath])  # Alternative: use 'mpg123' or 'ffplay'
        else:
            raise OSError("Unsupported operating system")
    except Exception as e:
        print(f"An error occurred while trying to play the audio: {e}")