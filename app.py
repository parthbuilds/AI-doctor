import os
import sys

# Ensure temporary directory is writable in serverless environments
os.environ.setdefault("GRADIO_TEMP_DIR", "/tmp")
os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")
os.environ.setdefault("MPLCONFIGDIR", "/tmp")

# Ensure root directory is in the Python path so imports resolve correctly
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
import gradio as gr
import uvicorn
from frontend.app import iface

app = FastAPI(title="AI Doctor API")

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "AI Doctor"}

# Mount the Gradio interface at the root path "/"
uploads_dir = "/tmp" if os.environ.get("VERCEL") else os.path.join(CURRENT_DIR, "uploads")
app = gr.mount_gradio_app(app, iface, path="/", allowed_paths=[uploads_dir, "/tmp"])

if __name__ == "__main__":
    os.makedirs(os.path.join(CURRENT_DIR, "uploads"), exist_ok=True)
    port = int(os.environ.get("PORT", 7860))
    print(f"Starting AI Doctor server on http://localhost:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)



