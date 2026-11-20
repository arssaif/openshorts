"""
Pipeline Orchestrator:
Coordinates downloading, transcription, virality scoring, vertical reframing,
anti-copyright protection, dynamic subtitles, and SEO generation.
"""
import uuid
import time
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable

from backend.config import EXPORTS_DIR, TEMP_DIR, DEFAULT_CLIP_DURATION
from backend.modules.downloader import VideoDownloader
from backend.modules.transcriber import AudioTranscriber
from backend.modules.analyzer import ViralityAnalyzer
from backend.modules.reframer import VideoReframer
from backend.modules.anti_copyright import AntiCopyrightShield
from backend.modules.subtitles import SubtitleEngine
from backend.modules.seo_generator import SEOGenerator

logger = logging.getLogger(__name__)

class ClippingPipeline:
    def __init__(self):
        self.downloader = VideoDownloader()
        self.transcriber = AudioTranscriber()
        self.analyzer = ViralityAnalyzer()
        self.reframer = VideoReframer()
        self.anti_copyright = AntiCopyrightShield()
        self.subtitles = SubtitleEngine()
        self.seo = SEOGenerator()

    def process(
        self,
        url_or_file: str,
        target_clips: int = 3,
        clip_duration: float = 40.0,
        layout: str = "split",
        enable_anti_copyright: bool = True,
        subtitle_style: str = "hormozi",
        video_section: str = "full",
        progress_cb: Optional[Callable[[str, int], None]] = None
    ) -> Dict[str, Any]:
        """
        Runs the end-to-end autonomous clipping pipeline.
        """
        job_id = str(uuid.uuid4())[:8]
        start_clock = time.time()

        def update(msg: str, pct: int):
            logger.info(f"[{pct}%] {msg}")
            if progress_cb:
                progress_cb(msg, pct)

        update("Starting GTA 6 Clipping Job...", 5)

        # 1. Video Ingestion
        is_local = Path(url_or_file).exists()
        section_offset = 0.0
        timestamp_comments = []

        if is_local:
            update("Loading local video file...", 15)
            video_path = str(Path(url_or_file).resolve())
            video_title = Path(url_or_file).stem
            # Probe duration with ffprobe
            import subprocess
            probe = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_path],
                capture_output=True, text=True
            )
            raw_duration = float(probe.stdout.strip() or 60.0)
            duration = raw_duration
            sub_path = None

            # Fast section slicing for long local gameplay videos (> 10 mins)
            if video_section in ["first_half", "middle", "last_half"] and raw_duration > 600.0:
                if video_section == "first_half":
                    sec_start, sec_end = 0.0, raw_duration * 0.5
                elif video_section == "middle":
                    sec_start, sec_end = raw_duration * 0.25, raw_duration * 0.75
                elif video_section == "last_half":
                    sec_start, sec_end = raw_duration * 0.5, raw_duration

                slice_dur = sec_end - sec_start
                if slice_dur > 2100.0:
                    if video_section == "last_half":
                        sec_start = max(sec_start, sec_end - 2100.0)
                    elif video_section == "middle":
                        mid = (sec_start + sec_end) / 2.0
                        sec_start = max(sec_start, mid - 1050.0)
                    sec_end = min(sec_end, sec_start + 2100.0)
                    slice_dur = sec_end - sec_start

                trimmed_local = str(TEMP_DIR / f"section_{job_id}.mp4")
                update(f"Trimming local file section '{video_section}' ({int(sec_start//60)}m-{int(sec_end//60)}m)...", 18)
                subprocess.run(
                    ["ffmpeg", "-y", "-ss", str(sec_start), "-t", str(slice_dur), "-i", video_path, "-c", "copy", trimmed_local],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                if Path(trimmed_local).exists() and Path(trimmed_local).stat().st_size > 1000:
                    video_path = trimmed_local
                    duration = slice_dur
                    section_offset = sec_start
        else:
            update(f"Analyzing stream & audience reactions: {url_or_file}", 10)
            meta = self.downloader.download_video(url_or_file, video_section=video_section, on_progress=update)
            video_path = meta["video_path"]
            video_title = meta["title"]
            duration = float(meta["duration"] or 120.0)
            sub_path = meta.get("subtitle_path")
            section_offset = float(meta.get("section_offset", 0.0))
            timestamp_comments = meta.get("timestamp_comments", [])

        # 2. Transcription
        update("Extracting high-precision word timestamps...", 35)
        transcript = self.transcriber.transcribe_audio(
            video_path,
            subtitle_path=sub_path,
            on_progress=update
        )

        # 3. AI Virality & Peak Action Detection
        update("Scanning action peaks, loudness spikes and audience excitement...", 50)
        top_moments = self.analyzer.find_top_clips(
            video_path=video_path,
            total_duration=duration,
            transcript_segments=transcript,
            target_clips=target_clips,
            clip_duration=clip_duration,
            timestamp_comments=timestamp_comments,
            section_offset=section_offset,
            on_progress=update
        )

        # 4. Rendering & Transformation
        self.subtitles.style = subtitle_style
        results = []
        step_increment = 30 // max(1, len(top_moments))

        for idx, moment in enumerate(top_moments):
            current_pct = 65 + (idx * step_increment)
            update(f"Rendering Clip #{idx+1} (Virality Score: {moment['score']}%) into 9:16...", current_pct)

            clip_filename = f"gta6_clip_{job_id}_{idx+1}.mp4"
            final_clip_path = str(EXPORTS_DIR / clip_filename)
            raw_rendered_path = str(TEMP_DIR / f"raw_{clip_filename}")

            # Anti-copyright filter chains
            v_filter = self.anti_copyright.get_video_filter_chain() if enable_anti_copyright else None
            a_filter = self.anti_copyright.get_audio_filter_chain() if enable_anti_copyright else None

            # Reframe to 9:16
            self.reframer.render_clip(
                input_video=video_path,
                output_path=raw_rendered_path,
                start_time=moment["start"],
                duration=moment["duration"],
                layout=layout,
                anti_copyright_vfilter=v_filter,
                anti_copyright_afilter=a_filter
            )

            # Subtitles
            if moment.get("transcript"):
                update(f"Applying animated {subtitle_style.upper()} subtitles to Clip #{idx+1}...", current_pct + 2)
                # Bake subtitles onto video
                self.subtitles.apply_subtitles_to_video(
                    input_video=raw_rendered_path,
                    output_video=final_clip_path,
                    segments=moment["transcript"],
                    start_offset=moment["start"],
                    duration=moment["duration"]
                )
            else:
                # No speech, move raw vertical directly
                import shutil
                shutil.move(raw_rendered_path, final_clip_path)

            # SEO Generation
            seo_assets = self.seo.generate_all_metadata(
                video_title=video_title,
                clip_index=idx,
                hook_text=moment["hook_text"],
                score=moment["score"],
                reasons=moment["reasons"]
            )

            results.append({
                "clip_id": f"{job_id}_{idx+1}",
                "filename": clip_filename,
                "file_path": final_clip_path,
                "url": f"/api/clips/{clip_filename}",
                "start": moment["start"],
                "end": moment["end"],
                "absolute_start": round(moment["start"] + section_offset, 2),
                "absolute_end": round(moment["end"] + section_offset, 2),
                "duration": moment["duration"],
                "score": moment["score"],
                "reasons": moment["reasons"],
                "hook_text": moment["hook_text"],
                "seo": seo_assets
            })

        update("All clips successfully generated and SEO-optimized! 🎉", 100)
        elapsed = round(time.time() - start_clock, 2)

        return {
            "job_id": job_id,
            "video_title": video_title,
            "total_duration": duration,
            "elapsed_seconds": elapsed,
            "clips": results
        }

