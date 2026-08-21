from dotenv import load_dotenv
load_dotenv()

import os
import base64
import logging
from groq import Groq

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DEFAULT_VISION_MODEL = "llama-3.2-11b-vision-preview"
DEFAULT_TEXT_MODEL = "llama-3.3-70b-versatile"

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
    Analyze image with query or perform text-only analysis via Groq.
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return "Error: GROQ_API_KEY is not set. Please set your GROQ_API_KEY in the .env file."

    client = Groq(api_key=api_key)

    # Determine model and build message structure
    if encoded_image:
        target_model = model or DEFAULT_VISION_MODEL
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": query
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{encoded_image}",
                        },
                    },
                ],
            }
        ]
    else:
        target_model = DEFAULT_TEXT_MODEL
        messages = [
            {
                "role": "user",
                "content": query
            }
        ]

    try:
        chat_completion = client.chat.completions.create(
            messages=messages,
            model=target_model
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        logging.error(f"Groq API call failed with model {target_model}: {e}")
        # Try fallback model if vision model failed
        if encoded_image and target_model != "llama-3.2-90b-vision-preview":
            try:
                logging.info("Retrying with llama-3.2-90b-vision-preview...")
                chat_completion = client.chat.completions.create(
                    messages=messages,
                    model="llama-3.2-90b-vision-preview"
                )
                return chat_completion.choices[0].message.content
            except Exception as e2:
                logging.error(f"Fallback vision model also failed: {e2}")
        elif not encoded_image and target_model != "llama-3.1-8b-instant":
            try:
                logging.info("Retrying with llama-3.1-8b-instant...")
                chat_completion = client.chat.completions.create(
                    messages=messages,
                    model="llama-3.1-8b-instant"
                )
                return chat_completion.choices[0].message.content
            except Exception as e2:
                logging.error(f"Fallback text model also failed: {e2}")
        return f"Medical analysis service temporarily unavailable: {e}"

