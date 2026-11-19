"""
Configuration module for GTA 6 Viral Clipper (PulseClip AI).
"""
import os
import shutil
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage"
DOWNLOADS_DIR = STORAGE_DIR / "downloads"
TEMP_DIR = STORAGE_DIR / "temp"
EXPORTS_DIR = STORAGE_DIR / "exports"
ASSETS_DIR = BASE_DIR / "assets"
GAMEPLAY_DIR = ASSETS_DIR / "gameplay"
UI_DIR = BASE_DIR / "ui"

for d in [STORAGE_DIR, DOWNLOADS_DIR, TEMP_DIR, EXPORTS_DIR, ASSETS_DIR, GAMEPLAY_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Hardware Acceleration Check (Apple Silicon VideoToolbox vs CPU libx264)
def detect_video_encoder() -> str:
    # Check if videotoolbox is available
    if shutil.which("ffmpeg"):
        try:
            import subprocess
            out = subprocess.run(
                ["ffmpeg", "-encoders"],
                capture_output=True,
                text=True,
                check=False
            ).stdout
            if "h264_videotoolbox" in out:
                return "h264_videotoolbox"
        except Exception:
            pass
    return "libx264"

VIDEO_ENCODER = detect_video_encoder()

# Video Export Defaults
TARGET_WIDTH = 1080
TARGET_HEIGHT = 1920
TARGET_FPS = 30
DEFAULT_CLIP_DURATION = 45  # seconds (sweet spot for Reels / Shorts / TikTok)

# Presets
PRESETS = {
    "gta6_viral": {
        "name": "GTA 6 Viral Short",
        "description": "High-octane action, split or blurred layout, punchy karaoke subtitles, anti-copyright transform",
        "layout": "split",
        "anti_copyright": True,
        "subtitle_style": "hormozi",
        "clip_duration": 40,
    },
    "story_cutscene": {
        "name": "Story & Dialogue",
        "description": "Cinematic ambient blur layout, high speech focus, elegant subtitles",
        "layout": "blur",
        "anti_copyright": True,
        "subtitle_style": "vice_city",
        "clip_duration": 50,
    },
    "action_montage": {
        "name": "Pure Gameplay Action",
        "description": "Smart centered crop, rapid cut detection, high-contrast subtitles",
        "layout": "crop",
        "anti_copyright": True,
        "subtitle_style": "hormozi",
        "clip_duration": 35,
    }
}

