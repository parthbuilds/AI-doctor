# if you dont use pipenv uncomment the following:
from dotenv import load_dotenv
load_dotenv()

#VoiceBot UI with Gradio
import os
import sys
import gradio as gr
import shutil
import time
import re
from datetime import datetime

CURRENT_DIR = os.path.dirname(__file__)
PARENT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, '..'))
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from backend.brain_of_the_doctor import encode_image, analyze_image_with_query
from backend.voice_of_the_patient import record_audio, transcribe_with_groq
from backend.voice_of_the_doctor import text_to_speech_with_gtts, text_to_speech_with_elevenlabs

#load_dotenv()

system_prompt="""You have to act as a professional doctor (for learning purposes). 
            What's in this image? Do you find anything medically concerning? Keep your main response concise (max 2 sentences), natural, and talk directly to the person.
            After the main response, include a section titled 'Recommendations:' on a new line, followed by 3-6 bullet points using hyphens. Do not number them.
            Do not say 'In the image I see'; instead say 'With what I see, I think you have ...'.
            The final format must be: two sentences of advice, then a newline, then 'Recommendations:' and bullet points starting with '-'"""


def process_inputs(audio_filepath, image_filepath):
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    uploads_dir = os.path.join(base_dir, 'uploads')
    os.makedirs(uploads_dir, exist_ok=True)

    saved_audio_path = None
    if audio_filepath:
        # Preserve original extension if present
        _, ext = os.path.splitext(audio_filepath)
        if not ext:
            ext = ".wav"
        timestamp = int(time.time())
        saved_audio_path = os.path.join(uploads_dir, f"input_audio_{timestamp}{ext}")
        try:
            shutil.copy(audio_filepath, saved_audio_path)
        except Exception:
            # Fallback: attempt move if copy fails
            try:
                shutil.move(audio_filepath, saved_audio_path)
            except Exception:
                saved_audio_path = audio_filepath  # last resort: keep original path

    speech_to_text_output = transcribe_with_groq(GROQ_API_KEY=os.environ.get("GROQ_API_KEY"), 
                                                audio_filepath=saved_audio_path or audio_filepath,
                                                stt_model="whisper-large-v3")

    # Handle the image input
    if image_filepath:
        doctor_response = analyze_image_with_query(query=system_prompt+"\n\nPatient says: \n"+speech_to_text_output, encoded_image=encode_image(image_filepath), model="meta-llama/llama-4-scout-17b-16e-instruct") #model="meta-llama/llama-4-maverick-17b-128e-instruct") 
    else:
        doctor_response = "No image provided for me to analyze"

    # Extract recommendations (lines after a 'Recommendations:' header or starting with bullet markers)
    def extract_recommendations(text: str) -> str:
        lines = text.splitlines()
        rec_start = -1
        for idx, line in enumerate(lines):
            if line.strip().lower().startswith("recommendations:"):
                rec_start = idx + 1
                break
        bullets = []
        source = lines[rec_start:] if rec_start != -1 else lines
        for line in source:
            s = line.strip()
            if s.startswith("-") or s.startswith("*") or s.startswith("•"):
                bullets.append("- " + s.lstrip("-*• "))
        if not bullets:
            # Fallback: split sentences and present as bullets
            sentences = re.split(r"(?<=[.!?])\s+", text.strip())
            bullets = [f"- {s}" for s in sentences if s and len(s) > 8][:5]
        return "\n".join(bullets)

    recommendations_md = extract_recommendations(doctor_response)

    # TTS for doctor's response
    output_audio_path = os.path.join(uploads_dir, 'final.mp3')
    voice_of_doctor = text_to_speech_with_elevenlabs(input_text=doctor_response, output_filepath=output_audio_path, speed=1.35) 

    # Generate a recommendations document
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    doc_path = os.path.join(uploads_dir, f"recommendations_{timestamp}.md")
    try:
        with open(doc_path, 'w', encoding='utf-8') as f:
            f.write(f"# Visit Summary and Recommendations\n\n")
            if saved_audio_path:
                f.write(f"Recorded speech file: {os.path.basename(saved_audio_path)}\n\n")
            if image_filepath:
                f.write(f"Submitted image file: {os.path.basename(image_filepath)}\n\n")
            f.write("## Transcription\n\n")
            f.write(speech_to_text_output + "\n\n")
            f.write("## Doctor's Response\n\n")
            f.write(doctor_response + "\n\n")
            f.write("## Recommendations\n\n")
            f.write(recommendations_md + "\n")
    except Exception:
        doc_path = None

    return speech_to_text_output, doctor_response, recommendations_md, voice_of_doctor, doc_path


# Create the interface
iface = gr.Interface(
    fn=process_inputs,
    inputs=[
        gr.Audio(sources=["microphone"], type="filepath"),
        gr.Image(type="filepath")
    ],
    outputs=[
        gr.Textbox(label="Speech to Text"),
        gr.Textbox(label="Doctor's Response"),
        gr.Markdown(label="Possible Solutions"),
        gr.Audio(),
        gr.File(label="Download Recommendations")
    ],
    title="AI Doctor"
)

iface.launch(debug=True, allowed_paths=[os.path.join(PARENT_DIR, 'uploads')])

#http://127.0.0.1:7860