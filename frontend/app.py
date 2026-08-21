from dotenv import load_dotenv
load_dotenv()

import os
import sys
import shutil
import time
import re
from datetime import datetime
import gradio as gr

CURRENT_DIR = os.path.dirname(__file__)
PARENT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, '..'))
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from backend.brain_of_the_doctor import encode_image, analyze_image_with_query
from backend.voice_of_the_patient import transcribe_with_groq
from backend.voice_of_the_doctor import text_to_speech_with_elevenlabs

SYSTEM_PROMPT = """You are an empathetic, professional AI medical assistant (for educational and informational purposes).
Review the patient's symptoms and/or image carefully. Provide your direct clinical assessment concisely (2-3 sentences max), addressing the patient directly.
After your main response, add a section titled 'Recommendations:' on a new line, followed by 3-5 actionable bullet points starting with '- '.
Do not say 'In the image I see'; instead say 'Based on what I observe, ...' or 'Based on your symptoms, ...'.
Always remind the patient to consult a certified healthcare professional for urgent or severe conditions."""


def process_inputs(audio_filepath, image_filepath):
    if os.environ.get("VERCEL"):
        uploads_dir = "/tmp"
    else:
        uploads_dir = os.path.join(PARENT_DIR, 'uploads')
    os.makedirs(uploads_dir, exist_ok=True)

    # 1. Check for completely empty inputs
    if not audio_filepath and not image_filepath:
        return (
            "No audio recorded.",
            "Please record your voice describing your symptoms or upload an image for evaluation.",
            "- Record an audio message explaining your symptoms.\n- Or upload a clear photo of the visible symptoms.\n- Press Submit to get a medical assessment.",
            None,
            None
        )

    # 2. Process audio if available
    saved_audio_path = None
    speech_to_text_output = ""
    if audio_filepath and os.path.exists(audio_filepath):
        _, ext = os.path.splitext(audio_filepath)
        if not ext:
            ext = ".wav"
        timestamp = int(time.time())
        saved_audio_path = os.path.join(uploads_dir, f"input_audio_{timestamp}{ext}")
        try:
            shutil.copy(audio_filepath, saved_audio_path)
        except Exception:
            try:
                shutil.move(audio_filepath, saved_audio_path)
            except Exception:
                saved_audio_path = audio_filepath

        speech_to_text_output = transcribe_with_groq(
            audio_filepath=saved_audio_path or audio_filepath,
            stt_model="whisper-large-v3"
        )
    else:
        speech_to_text_output = "No audio provided. Consultation based on visual input."

    # 3. Formulate query and perform LLM analysis
    encoded_img = encode_image(image_filepath) if image_filepath else None
    
    if encoded_img and speech_to_text_output and speech_to_text_output != "No audio provided. Consultation based on visual input.":
        query = f"{SYSTEM_PROMPT}\n\nPatient voice description:\n\"{speech_to_text_output}\"\n\nPlease analyze both the symptoms described and the attached image."
    elif encoded_img:
        query = f"{SYSTEM_PROMPT}\n\nPatient submitted this image for medical analysis. Please evaluate what is visible and provide recommendations."
    else:
        query = f"{SYSTEM_PROMPT}\n\nPatient describes their symptoms:\n\"{speech_to_text_output}\"\n\nPlease evaluate these symptoms and provide clinical recommendations."

    doctor_response = analyze_image_with_query(query=query, encoded_image=encoded_img)

    # 4. Extract bullet recommendations
    def extract_recommendations(text: str) -> str:
        if not text:
            return "- Consult a doctor for in-person evaluation."
        lines = text.splitlines()
        rec_start = -1
        for idx, line in enumerate(lines):
            if "recommendations" in line.lower():
                rec_start = idx + 1
                break
        bullets = []
        source = lines[rec_start:] if rec_start != -1 else lines
        for line in source:
            s = line.strip()
            if s.startswith("-") or s.startswith("*") or s.startswith("•") or (len(s) > 2 and s[0].isdigit() and s[1] in ".-)"):
                clean = re.sub(r"^[-*•\d.)\s]+", "", s)
                if clean:
                    bullets.append(f"- {clean}")
        if not bullets:
            sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) > 10]
            bullets = [f"- {s}" for s in sentences[-4:]]
        return "\n".join(bullets) if bullets else "- Consult a healthcare professional for accurate diagnosis."

    recommendations_md = extract_recommendations(doctor_response)

    # 5. Generate Voice of Doctor (TTS)
    output_audio_path = os.path.join(uploads_dir, f"doctor_voice_{int(time.time())}.mp3")
    # Use spoken portion (before recommendations header) for natural audio
    speech_text = doctor_response.split("Recommendations:")[0].strip() if "Recommendations:" in doctor_response else doctor_response
    voice_of_doctor = text_to_speech_with_elevenlabs(input_text=speech_text, output_filepath=output_audio_path, speed=1.1)

    # 6. Generate downloadable summary
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    doc_path = os.path.join(uploads_dir, f"visit_summary_{timestamp}.md")
    try:
        with open(doc_path, 'w', encoding='utf-8') as f:
            f.write("# 🩺 AI Doctor Visit Summary\n\n")
            f.write(f"*Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}*\n\n---\n\n")
            f.write("### 🗣️ Patient Voice / Description\n\n")
            f.write(f"{speech_to_text_output}\n\n")
            f.write("### 👨‍⚕️ Clinical Assessment\n\n")
            f.write(f"{doctor_response}\n\n")
            f.write("### 📋 Actionable Recommendations\n\n")
            f.write(f"{recommendations_md}\n\n")
            f.write("---\n*Disclaimer: This AI consultation is for informational and educational purposes only. Always consult a qualified medical professional for diagnosis and treatment.*")
    except Exception:
        doc_path = None

    return speech_to_text_output, doctor_response, recommendations_md, voice_of_doctor, doc_path


# Polished Gradio Interface
custom_theme = gr.themes.Soft(
    primary_hue="teal",
    secondary_hue="blue",
    neutral_hue="slate"
)

iface = gr.Interface(
    fn=process_inputs,
    inputs=[
        gr.Audio(sources=["microphone", "upload"], type="filepath", label="🎙️ Patient Voice (Microphone or Audio File)"),
        gr.Image(type="filepath", label="📷 Medical Image / Symptom Photo")
    ],
    outputs=[
        gr.Textbox(label="📝 Speech-to-Text Transcription", lines=3),
        gr.Textbox(label="🩺 Doctor's Assessment", lines=5),
        gr.Markdown(label="📋 Recommendations & Next Steps"),
        gr.Audio(label="🔊 Doctor's Spoken Response", type="filepath"),
        gr.File(label="📄 Download Visit Summary (.md)")
    ],
    title="🩺 AI Doctor — Multimodal Voice & Vision Medical Assistant",
    description="Speak into the microphone or upload an image of your condition. The AI Doctor transcribes your voice, analyzes visual signs with multimodal AI, speaks back with voice synthesis, and generates a visit summary.",
    flagging_mode="never"
)

if __name__ == "__main__":
    uploads_path = os.path.join(PARENT_DIR, 'uploads')
    os.makedirs(uploads_path, exist_ok=True)
    iface.launch(
        theme=custom_theme,
        debug=True,
        allowed_paths=[uploads_path],
        server_name="0.0.0.0",
        server_port=7860
    )