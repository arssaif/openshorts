"""
Downloader module using yt-dlp to fetch YouTube video, audio, and captions.
Uses modern extractor-args for Android/Web clients to prevent bot checks.
"""
import os
import sys
import shutil
import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List
from backend.config import DOWNLOADS_DIR, TEMP_DIR
from backend.modules.comment_analyzer import CommentAnalyzer

logger = logging.getLogger(__name__)

def get_ytdlp_cmd() -> str:
    """Finds the yt-dlp executable in the current venv, project root, or PATH."""
    venv_ytdlp = Path(sys.executable).parent / "yt-dlp"
    if venv_ytdlp.exists():
        return str(venv_ytdlp)
    local_venv = Path(__file__).resolve().parents[2] / ".venv" / "bin" / "yt-dlp"
    if local_venv.exists():
        return str(local_venv)
    which = shutil.which("yt-dlp")
    if which:
        return which
    return "yt-dlp"

class VideoDownloader:
    def __init__(self, output_dir: Path = DOWNLOADS_DIR):
        self.output_dir = output_dir
        self.comment_analyzer = CommentAnalyzer()

    def extract_info(self, url: str, fetch_comments: bool = True) -> Dict[str, Any]:
        """Extract metadata (and comments) without downloading media files."""
        ytdlp_bin = get_ytdlp_cmd()
        cmd = [
            ytdlp_bin,
            "--extractor-args", "youtube:player_client=android;max_comments=150",
            "--dump-json",
            "--no-playlist"
        ]
        if fetch_comments:
            cmd.append("--get-comments")
        cmd.append(url)

        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            logger.warning(f"Initial extract_info failed, retrying without extractor args: {res.stderr.strip()[:200]}")
            cmd_fallback = [ytdlp_bin, "--dump-json", "--no-playlist", url]
            res = subprocess.run(cmd_fallback, capture_output=True, text=True)
            if res.returncode != 0:
                raise RuntimeError(f"yt-dlp extract_info failed: {res.stderr.strip()}")

        return json.loads(res.stdout)

    def download_video(
        self,
        url: str,
        video_section: str = "full",
        on_progress=None
    ) -> Dict[str, Any]:
        """
        Download video + audio with smart section targeting (first_half, middle, last_half, full)
        and auto-extracts viewer comments and discussion spikes.
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        if on_progress:
            on_progress("Extracting stream metadata & audience discussion comments...", 10)

        info = self.extract_info(url, fetch_comments=True)
        video_id = info.get("id")
        video_title = info.get("title", "GTA 6 Video")
        video_duration = float(info.get("duration", 0) or 0)
        raw_comments = info.get("comments", [])

        # Parse timestamp comments & audience excitement
        timestamp_comments = self.comment_analyzer.parse_timestamp_comments(raw_comments)
        if on_progress and timestamp_comments:
            on_progress(f"Found {len(timestamp_comments)} viewer timestamp reactions in comments!", 13)

        output_template = str(self.output_dir / f"{video_id}.%(ext)s")

        # Determine target video section (first_half, middle, last_half, full)
        if video_section == "first_half":
            sec_start = 0.0
            sec_end = video_duration * 0.5
        elif video_section == "middle":
            sec_start = video_duration * 0.25
            sec_end = video_duration * 0.75
        elif video_section == "last_half":
            sec_start = video_duration * 0.5
            sec_end = video_duration
        else: # "full"
            sec_start = 0.0
            sec_end = video_duration

        section_len = max(1.0, sec_end - sec_start)

        # For long gameplay streams (> 30 mins in section), select high-energy window
        if section_len > 1800.0:
            # Check if comments highlight high discussion cluster in this section
            clusters = self.comment_analyzer.find_peak_discussion_clusters(timestamp_comments, sec_start, sec_end)
            if clusters and clusters[0]["count"] >= 2:
                top_center = clusters[0]["center_time"]
                dl_start = max(sec_start, top_center - 900.0)
                dl_end = min(sec_end, dl_start + 2100.0)
                if on_progress:
                    on_progress(f"Targeting {video_section.replace('_', ' ').title()} around crowd buzz ({int(top_center//60)}m)...", 15)
            else:
                if video_section == "first_half":
                    dl_start = 0.0
                    dl_end = min(sec_end, 2100.0)
                elif video_section == "middle":
                    mid = (sec_start + sec_end) / 2.0
                    dl_start = max(sec_start, mid - 1050.0)
                    dl_end = min(sec_end, mid + 1050.0)
                elif video_section == "last_half":
                    dl_start = max(sec_start, sec_end - 2100.0)
                    dl_end = sec_end
                else:
                    dl_start = 0.0
                    dl_end = min(video_duration, 2100.0)
        else:
            dl_start = sec_start
            dl_end = sec_end

        ytdlp_bin = get_ytdlp_cmd()
        cmd = [
            ytdlp_bin,
            "--extractor-args", "youtube:player_client=android",
            "-f", "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
            "--merge-output-format", "mp4",
            "--no-playlist",
            "-o", output_template
        ]

        section_offset = 0.0
        effective_duration = video_duration
        if dl_start > 0 or dl_end < video_duration:
            h1, m1, s1 = int(dl_start // 3600), int((dl_start % 3600) // 60), int(dl_start % 60)
            h2, m2, s2 = int(dl_end // 3600), int((dl_end % 3600) // 60), int(dl_end % 60)
            time_spec = f"*{h1:02d}:{m1:02d}:{s1:02d}-{h2:02d}:{m2:02d}:{s2:02d}"
            cmd.extend(["--download-sections", time_spec])
            section_offset = dl_start
            effective_duration = dl_end - dl_start
            if on_progress:
                on_progress(f"Smart clipping {video_section.replace('_', ' ').title()} window ({h1:02d}:{m1:02d}:{s1:02d} - {h2:02d}:{m2:02d}:{s2:02d})...", 18)

        cmd.append(url)

        stderr_lines = []
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in iter(process.stdout.readline, ''):
            stderr_lines.append(line)
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
        
        # Check if video was downloaded
        video_path = self.output_dir / f"{video_id}.mp4"
        if not video_path.exists():
            matches = list(self.output_dir.glob(f"{video_id}*"))
            video_matches = [m for m in matches if m.suffix in [".mp4", ".mkv", ".webm"] and not str(m).endswith(".part")]
            if video_matches:
                video_path = video_matches[0]
            else:
                # Primary download failed - try fallback format
                logger.warning(f"Primary download exited with code {process.returncode}. Output tail:\n" + "".join(stderr_lines[-10:]))
                if on_progress:
                    on_progress("Retrying download with adaptive format stream...", 22)
                fallback_cmd = [
                    ytdlp_bin,
                    "-f", "b/best[height<=1080]/best",
                    "--merge-output-format", "mp4",
                    "--no-playlist",
                    "-o", output_template
                ]
                if dl_start > 0 or dl_end < video_duration:
                    fallback_cmd.extend(["--download-sections", time_spec])
                fallback_cmd.append(url)
                fb_res = subprocess.run(fallback_cmd, capture_output=True, text=True)
                if fb_res.returncode != 0:
                    logger.error(f"Fallback download also failed: {fb_res.stderr.strip()[:300]}")
                
                # Check again
                if not video_path.exists():
                    matches = list(self.output_dir.glob(f"{video_id}*"))
                    video_matches = [m for m in matches if m.suffix in [".mp4", ".mkv", ".webm"] and not str(m).endswith(".part")]
                    if video_matches:
                        video_path = video_matches[0]
                    else:
                        err_tail = "\n".join(stderr_lines[-15:])
                        raise FileNotFoundError(f"Downloaded video file not found for video ID: {video_id}. yt-dlp output:\n{err_tail}")

        # Check subtitle files if available
        sub_files = list(self.output_dir.glob(f"{video_id}*.vtt")) + list(self.output_dir.glob(f"{video_id}*.json3"))
        sub_path = sub_files[0] if sub_files else None

        if on_progress:
            on_progress("Download and stream ingestion complete!", 35)

        return {
            "id": video_id,
            "title": video_title,
            "duration": effective_duration,
            "full_duration": video_duration,
            "video_path": str(video_path),
            "subtitle_path": str(sub_path) if sub_path else None,
            "description": info.get("description", ""),
            "uploader": info.get("uploader", ""),
            "section_offset": section_offset,
            "timestamp_comments": timestamp_comments,
            "raw_comments": raw_comments
        }
