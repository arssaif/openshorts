"""
Reframer module: Converts 16:9 landscape video into 9:16 vertical shorts
using Split Screen, Ambient Blur, or Smart Dynamic Crop layouts.
"""
import subprocess
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from backend.config import VIDEO_ENCODER, TARGET_WIDTH, TARGET_HEIGHT, TARGET_FPS

logger = logging.getLogger(__name__)

class VideoReframer:
    def __init__(self, encoder: str = VIDEO_ENCODER):
        self.encoder = encoder

    def build_filter_graph(
        self,
        layout: str = "split",
        anti_copyright_vfilter: Optional[str] = None,
        secondary_video_path: Optional[str] = None
    ) -> str:
        """
        Builds the FFmpeg complex filter graph for the chosen 9:16 layout.
        """
        # Base input [0:v] is the main video
        if layout == "blur":
            # 1. Background: scale to fill 1080x1920, blur heavily, darken
            # 2. Foreground: scale to 1080 width (1080x608), overlay on center
            fg_filter = anti_copyright_vfilter if anti_copyright_vfilter else "null"
            filter_str = (
                f"[0:v]split=2[bg_in][fg_in];"
                f"[bg_in]scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=increase,"
                f"crop={TARGET_WIDTH}:{TARGET_HEIGHT},boxblur=25:5,eq=brightness=-0.15[bg];"
                f"[fg_in]{fg_filter},scale={TARGET_WIDTH}:-1[fg];"
                f"[bg][fg]overlay=(W-w)/2:(H-h)/2[outv]"
            )
            return filter_str

        elif layout == "crop":
            # Direct 9:16 center crop
            fg_filter = anti_copyright_vfilter if anti_copyright_vfilter else "null"
            filter_str = (
                f"[0:v]{fg_filter},"
                f"scale=-1:{TARGET_HEIGHT},"
                f"crop={TARGET_WIDTH}:{TARGET_HEIGHT}:(in_w-{TARGET_WIDTH})/2:0[outv]"
            )
            return filter_str

        else: # "split" layout (Top: Main action, Bottom: Ambient/Action secondary)
            fg_filter = anti_copyright_vfilter if anti_copyright_vfilter else "null"
            half_height = TARGET_HEIGHT // 2  # 960

            if secondary_video_path and Path(secondary_video_path).exists():
                # [0:v] is main (top), [1:v] is secondary (bottom)
                filter_str = (
                    f"[0:v]{fg_filter},scale=-1:{half_height},"
                    f"crop={TARGET_WIDTH}:{half_height}:(in_w-{TARGET_WIDTH})/2:0[top];"
                    f"[1:v]scale=-1:{half_height},"
                    f"crop={TARGET_WIDTH}:{half_height}:(in_w-{TARGET_WIDTH})/2:0[bottom];"
                    f"[top][bottom]vstack=inputs=2[outv]"
                )
            else:
                # Mirror ambient dynamic crop for bottom
                filter_str = (
                    f"[0:v]{fg_filter},split=2[main_top][main_bot];"
                    f"[main_top]scale=-1:{half_height},"
                    f"crop={TARGET_WIDTH}:{half_height}:(in_w-{TARGET_WIDTH})/2:0[top];"
                    f"[main_bot]scale={TARGET_WIDTH}:{half_height}:force_original_aspect_ratio=increase,"
                    f"crop={TARGET_WIDTH}:{half_height},boxblur=15:3,eq=saturation=1.2:contrast=1.1[bottom];"
                    f"[top][bottom]vstack=inputs=2[outv]"
                )
            return filter_str

    def render_clip(
        self,
        input_video: str,
        output_path: str,
        start_time: float,
        duration: float,
        layout: str = "split",
        anti_copyright_vfilter: Optional[str] = None,
        anti_copyright_afilter: Optional[str] = None,
        secondary_video_path: Optional[str] = None
    ) -> str:
        """
        Executes FFmpeg with hardware acceleration to render the framed 9:16 vertical video.
        """
        filter_graph = self.build_filter_graph(
            layout=layout,
            anti_copyright_vfilter=anti_copyright_vfilter,
            secondary_video_path=secondary_video_path
        )

        cmd = ["ffmpeg", "-y"]

        # Fast seek before input
        cmd.extend(["-ss", str(start_time)])
        cmd.extend(["-t", str(duration)])
        cmd.extend(["-i", input_video])

        if secondary_video_path and Path(secondary_video_path).exists() and layout == "split":
            cmd.extend(["-ss", str(start_time)])
            cmd.extend(["-t", str(duration)])
            cmd.extend(["-i", secondary_video_path])

        cmd.extend(["-filter_complex", filter_graph])
        cmd.extend(["-map", "[outv]"])

        if anti_copyright_afilter:
            cmd.extend(["-af", anti_copyright_afilter])
        cmd.extend(["-map", "0:a?"])

        # Hardware acceleration encoder
        if self.encoder == "h264_videotoolbox":
            cmd.extend(["-c:v", "h264_videotoolbox", "-b:v", "7M", "-pix_fmt", "yuv420p"])
        else:
            cmd.extend(["-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p"])

        cmd.extend(["-c:a", "aac", "-b:a", "192k"])
        cmd.extend(["-r", str(TARGET_FPS)])
        cmd.append(output_path)

        logger.info(f"Rendering vertical clip with FFmpeg: {' '.join(cmd)}")
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            logger.error(f"FFmpeg error: {res.stderr}")
            # Try fallback to libx264 if hardware encoder failed
            if self.encoder == "h264_videotoolbox":
                logger.info("Retrying with fallback libx264...")
                fallback_cmd = [arg if arg != "h264_videotoolbox" else "libx264" for arg in cmd]
                res2 = subprocess.run(fallback_cmd, capture_output=True, text=True)
                if res2.returncode != 0:
                    raise RuntimeError(f"FFmpeg fallback failed: {res2.stderr}")
            else:
                raise RuntimeError(f"FFmpeg render failed: {res.stderr}")

        return output_path

