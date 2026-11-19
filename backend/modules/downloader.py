"""
Downloader module using yt-dlp to fetch YouTube video, audio, and captions.
Uses modern extractor-args for Android/Web clients to prevent bot checks.
"""
import os
import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from backend.config import DOWNLOADS_DIR, TEMP_DIR

logger = logging.getLogger(__name__)

class VideoDownloader:
    def __init__(self, output_dir: Path = DOWNLOADS_DIR):
        self.output_dir = output_dir

    def extract_info(self, url: str) -> Dict[str, Any]:
        """Extract metadata without downloading."""
        cmd = [
            "yt-dlp",
            "--extractor-args", "youtube:player_client=android,web",
            "--dump-json",
            "--no-playlist",
            url
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            # Fallback without extractor args
            cmd_fallback = ["yt-dlp", "--dump-json", "--no-playlist", url]
            res = subprocess.run(cmd_fallback, capture_output=True, text=True)
            if res.returncode != 0:
                raise RuntimeError(f"yt-dlp extract_info failed: {res.stderr.strip()}")

        return json.loads(res.stdout)

    def download_video(self, url: str, on_progress=None) -> Dict[str, Any]:
        """
        Download video + audio, plus auto-generated subtitles if present.
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        if on_progress:
            on_progress("Extracting YouTube stream information...", 10)

        info = self.extract_info(url)
        video_id = info.get("id")
        video_title = info.get("title", "GTA 6 Video")
        video_duration = float(info.get("duration", 0) or 0)

        output_template = str(self.output_dir / f"{video_id}.%(ext)s")

        if on_progress:
            on_progress(f"Downloading stream: '{video_title[:45]}...' ({int(video_duration//60)}m)", 15)

        cmd = [
            "yt-dlp",
            "--extractor-args", "youtube:player_client=android,web",
            "-f", "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
            "--merge-output-format", "mp4",
            "--write-auto-sub",
            "--sub-lang", "en",
            "--sub-format", "vtt/srv3/json3",
            "--no-playlist",
            "-o", output_template
        ]

        # For ultra long gameplay / walkthrough streams (> 20 mins), cap download to first 20 mins for fast processing
        effective_duration = video_duration
        if video_duration > 1200:
            if on_progress:
                on_progress(f"Long-form stream ({int(video_duration//60)}m): Smart clipping first 20m for viral hooks...", 18)
            cmd.extend(["--download-sections", "*00:00:00-00:20:00"])
            effective_duration = 1200.0

        cmd.append(url)

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in iter(process.stdout.readline, ''):
            if "%" in line:
                try:
                    parts = line.split("%")[0].split()
                    pct = float(parts[-1])
                    if on_progress:
                        scaled = 20 + int(pct * 0.15)
                        on_progress(f"Downloading media stream: {pct:.1f}%", scaled)
                except Exception:
                    pass
        process.wait()
        if process.returncode != 0:
            logger.warning("Download command returned non-zero, checking if file was created...")

        # Find downloaded video file
        video_path = self.output_dir / f"{video_id}.mp4"
        if not video_path.exists():
            matches = list(self.output_dir.glob(f"{video_id}*"))
            video_matches = [m for m in matches if m.suffix in [".mp4", ".mkv", ".webm"] and not str(m).endswith(".part")]
            if video_matches:
                video_path = video_matches[0]
            else:
                raise FileNotFoundError(f"Downloaded video file not found for video ID: {video_id}")

        # Check subtitle files
        sub_files = list(self.output_dir.glob(f"{video_id}*.vtt")) + list(self.output_dir.glob(f"{video_id}*.json3"))
        sub_path = sub_files[0] if sub_files else None

        if on_progress:
            on_progress("Download and stream ingestion complete!", 35)

        return {
            "id": video_id,
            "title": video_title,
            "duration": effective_duration,
            "video_path": str(video_path),
            "subtitle_path": str(sub_path) if sub_path else None,
            "description": info.get("description", ""),
            "uploader": info.get("uploader", ""),
        }
