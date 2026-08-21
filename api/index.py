import os
import sys

# Ensure temporary directory is writable in serverless environments
os.environ.setdefault("VERCEL", "1")
os.environ.setdefault("GRADIO_TEMP_DIR", "/tmp")
os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")
os.environ.setdefault("MPLCONFIGDIR", "/tmp")

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app import app

