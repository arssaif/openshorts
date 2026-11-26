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

    def compute_section_window(
        self,
        video_duration: float,
        video_section: str = "full",
        timestamp_comments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Computes non-overlapping section bounds and a max-35m download window.
        """
        if video_section == "first_half":
            sec_start = 0.0
            sec_end = video_duration / 3.0
        elif video_section == "middle":
            sec_start = video_duration / 3.0
            sec_end = video_duration * (2.0 / 3.0)
        elif video_section == "last_half":
            sec_start = video_duration * (2.0 / 3.0)
            sec_end = video_duration
        else:  # "full"
            sec_start = 0.0
            sec_end = video_duration

        section_len = max(1.0, sec_end - sec_start)
        crowd_center = None

        # For long gameplay streams (> 30 mins in section), select high-energy window
        if section_len > 1800.0:
            clusters = self.comment_analyzer.find_peak_discussion_clusters(
                timestamp_comments or [], sec_start, sec_end
            )
            if clusters and clusters[0]["count"] >= 2:
                top_center = clusters[0]["center_time"]
                crowd_center = top_center
                dl_start = max(sec_start, min(sec_end - 2100.0, top_center - 1050.0))
                dl_end = min(sec_end, dl_start + 2100.0)
            else:
                if video_section == "first_half":
                    dl_start = sec_start
                    dl_end = min(sec_end, sec_start + 2100.0)
                elif video_section == "middle":
                    mid = (sec_start + sec_end) / 2.0
                    dl_start = max(sec_start, mid - 1050.0)
                    dl_end = min(sec_end, dl_start + 2100.0)
                elif video_section == "last_half":
                    dl_start = max(sec_start, sec_end - 2100.0)
                    dl_end = sec_end
                else:
                    dl_start = 0.0
                    dl_end = min(video_duration, 2100.0)
        else:
            dl_start = sec_start
            dl_end = sec_end

        section_tag = f"{video_section}_{int(dl_start)}_{int(dl_end)}"
        return {
            "sec_start": sec_start,
            "sec_end": sec_end,
            "dl_start": dl_start,
            "dl_end": dl_end,
            "section_tag": section_tag,
            "crowd_center": crowd_center
        }

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

        window = self.compute_section_window(video_duration, video_section, timestamp_comments)
        dl_start = window["dl_start"]
        dl_end = window["dl_end"]
        section_tag = window["section_tag"]
        crowd_center = window["crowd_center"]

        if crowd_center is not None and on_progress:
            on_progress(f"Targeting {video_section.replace('_', ' ').title()} around crowd buzz ({int(crowd_center//60)}m)...", 15)

        target_stem = f"{video_id}_{section_tag}"
        output_template = str(self.output_dir / f"{target_stem}.%(ext)s")

        def _find_section_video() -> Optional[Path]:
            exact_mp4 = self.output_dir / f"{target_stem}.mp4"
            if exact_mp4.exists() and exact_mp4.stat().st_size > 10000:
                return exact_mp4
            matches = list(self.output_dir.glob(f"{target_stem}.*"))
            video_matches = [
                m for m in matches
                if m.suffix in [".mp4", ".mkv", ".webm"]
                and not str(m).endswith(".part")
                and m.stat().st_size > 10000
            ]
            return video_matches[0] if video_matches else None

        is_sliced = dl_start > 0 or dl_end < video_duration
        section_offset = dl_start if is_sliced else 0.0
        effective_duration = max(1.0, dl_end - dl_start) if is_sliced else video_duration

        cached_path = _find_section_video()
        if cached_path:
            video_path = cached_path
            if on_progress:
                on_progress(f"Using cached section video ({target_stem})...", 30)
        else:
            ytdlp_bin = get_ytdlp_cmd()
            cmd = [
                ytdlp_bin,
                "--extractor-args", "youtube:player_client=android",
                "-f", "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
                "--merge-output-format", "mp4",
                "--no-playlist",
                "--force-overwrites",
                "-o", output_template
            ]

            time_spec = None
            if is_sliced:
                h1, m1, s1 = int(dl_start // 3600), int((dl_start % 3600) // 60), int(dl_start % 60)
                h2, m2, s2 = int(dl_end // 3600), int((dl_end % 3600) // 60), int(dl_end % 60)
                time_spec = f"*{h1:02d}:{m1:02d}:{s1:02d}-{h2:02d}:{m2:02d}:{s2:02d}"
                cmd.extend(["--download-sections", time_spec])
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

            video_path = _find_section_video()
            if not video_path:
                # Primary download failed - try fallback format
                logger.warning(f"Primary download exited with code {process.returncode}. Output tail:\n" + "".join(stderr_lines[-10:]))
                if on_progress:
                    on_progress("Retrying download with adaptive format stream...", 22)
                fallback_cmd = [
                    ytdlp_bin,
                    "-f", "b/best[height<=1080]/best",
                    "--merge-output-format", "mp4",
                    "--no-playlist",
                    "--force-overwrites",
                    "-o", output_template
                ]
                if time_spec:
                    fallback_cmd.extend(["--download-sections", time_spec])
                fallback_cmd.append(url)
                fb_res = subprocess.run(fallback_cmd, capture_output=True, text=True)
                if fb_res.returncode != 0:
                    logger.error(f"Fallback download also failed: {fb_res.stderr.strip()[:300]}")

                video_path = _find_section_video()
                if not video_path:
                    err_tail = "\n".join(stderr_lines[-15:])
                    raise FileNotFoundError(f"Downloaded video file not found for section {target_stem}. yt-dlp output:\n{err_tail}")

        # Probe actual downloaded file duration
        try:
            probe = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)],
                capture_output=True, text=True
            )
            probed_dur = float(probe.stdout.strip() or 0)
            if probed_dur > 0:
                effective_duration = probed_dur
        except Exception:
            pass

        # Check subtitle files if available
        sub_files = list(self.output_dir.glob(f"{target_stem}*.vtt")) + list(self.output_dir.glob(f"{target_stem}*.json3"))
        if not sub_files:
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
