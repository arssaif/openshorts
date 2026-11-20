"""
FastAPI application for GTA 6 Viral Clipper.
Serves Web UI, REST endpoints, and SSE (Server-Sent Events) for real-time progress.
"""
import time
import json
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.config import BASE_DIR, EXPORTS_DIR, UI_DIR, DOWNLOADS_DIR, VIDEO_ENCODER, PRESETS
from backend.pipeline import ClippingPipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gta6_clipper")

app = FastAPI(title="GTA 6 Viral Clipper AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Active jobs state
jobs_state: Dict[str, Dict[str, Any]] = {}
pipeline = ClippingPipeline()

class ClipRequest(BaseModel):
    url: str
    target_clips: int = 3
    clip_duration: float = 40.0
    layout: str = "split" # "split", "blur", "crop"
    enable_anti_copyright: bool = True
    subtitle_style: str = "hormozi" # "hormozi", "vice_city", "clean"
    video_section: str = "full" # "full", "first_half", "middle", "last_half"

@app.get("/api/health")
async def health():
    return {
        "status": "online",
        "encoder": VIDEO_ENCODER,
        "presets": PRESETS,
        "export_count": len(list(EXPORTS_DIR.glob("*.mp4")))
    }

def run_job_task(job_id: str, req: ClipRequest):
    def on_progress(msg: str, pct: int):
        if job_id in jobs_state:
            jobs_state[job_id]["progress"] = pct
            jobs_state[job_id]["status_message"] = msg
            jobs_state[job_id]["events"].append({"time": time.time(), "msg": msg, "pct": pct})

    try:
        jobs_state[job_id]["status"] = "processing"
        result = pipeline.process(
            url_or_file=req.url,
            target_clips=req.target_clips,
            clip_duration=req.clip_duration,
            layout=req.layout,
            enable_anti_copyright=req.enable_anti_copyright,
            subtitle_style=req.subtitle_style,
            video_section=req.video_section,
            progress_cb=on_progress
        )
        jobs_state[job_id]["status"] = "completed"
        jobs_state[job_id]["result"] = result
        jobs_state[job_id]["progress"] = 100
    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}", exc_info=True)
        jobs_state[job_id]["status"] = "failed"
        jobs_state[job_id]["error"] = str(e)

@app.post("/api/clip")
async def create_clip_job(req: ClipRequest, bg_tasks: BackgroundTasks):
    import uuid
    job_id = str(uuid.uuid4())[:8]
    jobs_state[job_id] = {
        "id": job_id,
        "status": "queued",
        "progress": 0,
        "status_message": "Queued for processing...",
        "events": [],
        "request": req.model_dump(),
        "result": None,
        "error": None
    }
    bg_tasks.add_task(run_job_task, job_id, req)
    return {"job_id": job_id, "status": "queued"}

@app.post("/api/upload")
async def upload_local_video(file: UploadFile = File(...)):
    """Uploads a local video for clipping."""
    dest_path = DOWNLOADS_DIR / file.filename
    with open(dest_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            f.write(chunk)
    return {"file_path": str(dest_path), "filename": file.filename}

@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str):
    if job_id not in jobs_state:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs_state[job_id]

@app.get("/api/jobs/{job_id}/stream")
async def stream_job_events(job_id: str):
    """Server-Sent Events (SSE) for live streaming progress updates."""
    if job_id not in jobs_state:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        last_pct = -1
        while True:
            if job_id not in jobs_state:
                break
            job = jobs_state[job_id]
            pct = job.get("progress", 0)
            msg = job.get("status_message", "")
            status = job.get("status", "processing")

            if pct != last_pct or status in ["completed", "failed"]:
                data = json.dumps({
                    "progress": pct,
                    "message": msg,
                    "status": status,
                    "result": job.get("result") if status == "completed" else None,
                    "error": job.get("error") if status == "failed" else None
                })
                yield f"data: {data}\n\n"
                last_pct = pct

            if status in ["completed", "failed"]:
                break
            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/api/clips/{filename}")
async def get_clip_file(filename: str):
    clip_path = EXPORTS_DIR / filename
    if not clip_path.exists():
        raise HTTPException(status_code=404, detail="Clip file not found")
    return FileResponse(clip_path, media_type="video/mp4", filename=filename)

# Serve UI Static Assets
app.mount("/static", StaticFiles(directory=str(UI_DIR)), name="static")

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = UI_DIR / "index.html"
    if not index_file.exists():
        return "<h1>GTA 6 Clipper UI loading...</h1>"
    with open(index_file, "r", encoding="utf-8") as f:
        return f.read()

