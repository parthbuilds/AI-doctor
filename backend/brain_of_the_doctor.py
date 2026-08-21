import os
import base64
import logging
from dotenv import load_dotenv

# Ensure .env is reliably loaded regardless of execution cwd
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
load_dotenv()

from groq import Groq

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DEFAULT_TEXT_MODEL = "openai/gpt-oss-120b"
FALLBACK_TEXT_MODEL = "openai/gpt-oss-20b"
VISION_MODELS = ["llama-3.2-11b-vision-preview", "llama-3.2-90b-vision-preview"]

def encode_image(image_path):
    """Safely convert an image file to base64 encoding."""
    if not image_path or not os.path.exists(image_path):
        return None
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        logging.error(f"Error encoding image {image_path}: {e}")
        return None

def analyze_image_with_query(query, model=None, encoded_image=None):
    """
    Analyze patient symptoms and image using Groq LLM.
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return "Error: GROQ_API_KEY is not set. Please set your GROQ_API_KEY in the .env file."

    client = Groq(api_key=api_key)

    # 1. If image is present, try vision models first if available
    if encoded_image:
        for v_model in VISION_MODELS:
            try:
                chat_completion = client.chat.completions.create(
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": query},
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"}},
                            ],
                        }
                    ],
                    model=v_model
                )
                return chat_completion.choices[0].message.content
            except Exception:
                continue

    # 2. Text-based clinical analysis with high-capability model
    target_models = [model or DEFAULT_TEXT_MODEL, FALLBACK_TEXT_MODEL, "groq/compound", "qwen/qwen3.6-27b"]
    last_err = None

    for m in target_models:
        if not m:
            continue
        try:
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": query}],
                model=m
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            last_err = e
            logging.warning(f"Groq model {m} failed: {e}. Trying fallback...")

    return f"Medical analysis service temporarily unavailable: {last_err}"


