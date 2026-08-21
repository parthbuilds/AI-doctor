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

try:
    from app import app
except Exception as e:
    import traceback
    err_tb = traceback.format_exc()
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse, JSONResponse
    
    app = FastAPI(title="AI Doctor Diagnostic")

    @app.get("/api/health")
    def health_err():
        return JSONResponse({"status": "startup_error", "error": str(e), "traceback": err_tb}, status_code=500)

    @app.get("/{full_path:path}")
    def fallback(full_path: str):
        return HTMLResponse(f"<h3>AI Doctor Serverless Error</h3><pre>{err_tb}</pre>", status_code=500)


