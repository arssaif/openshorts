"""
Dynamic Subtitle Engine:
Generates Alex Hormozi / MrBeast & Vice City styled word-by-word animated karaoke subtitles.
Outputs ASS files, Remotion timeline JSON, and rendered transparent overlay images for FFmpeg.
"""
import os
import json
import logging
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Tuple
from PIL import Image, ImageDraw, ImageFont
from backend.config import TARGET_WIDTH, TARGET_HEIGHT, TEMP_DIR

logger = logging.getLogger(__name__)

# Font candidate locations on macOS and Linux
FONT_PATHS = [
    "/System/Library/Fonts/Supplemental/Arial Black.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial Black.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
]

def get_font(size: int = 46) -> ImageFont.FreeTypeFont:
    for fp in FONT_PATHS:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
    return ImageFont.load_default()

class SubtitleEngine:
    def __init__(self, style: str = "hormozi"):
        self.style = style # "hormozi" or "vice_city" or "clean"

    def generate_ass_subtitles(
        self,
        segments: List[Dict[str, Any]],
        output_ass_path: str,
        start_offset: float = 0.0
    ) -> str:
        """
        Generates an ASS (Advanced SubStation Alpha) file with word-by-word karaoke highlighting.
        """
        # Hormozi: Primary White (&HFFFFFF), Outline Black (&H000000), Highlight Yellow (&H00E5FF)
        header = f"""[Script Info]
Title: GTA 6 Viral Subtitles
ScriptType: v4.00+
PlayResX: {TARGET_WIDTH}
PlayResY: {TARGET_HEIGHT}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Hormozi,Arial Black,54,&H00FFFFFF,&H0000E5FF,&H00000000,&H90000000,1,0,0,0,100,100,2,0,1,6,3,2,40,40,240,1
Style: ViceCity,Arial Black,54,&H0000FFFF,&H007F00FF,&H00000000,&H90000000,1,0,0,0,100,100,2,0,1,6,3,2,40,40,240,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        def format_time(sec: float) -> str:
            sec = max(0.0, sec - start_offset)
            h = int(sec // 3600)
            m = int((sec % 3600) // 60)
            s = sec % 60
            return f"{h}:{m:02d}:{s:05.2f}"

        events = []
        chosen_style = "ViceCity" if self.style == "vice_city" else "Hormozi"

        for seg in segments:
            words = seg.get("words", [])
            if not words:
                continue

            seg_start = words[0]["start"]
            seg_end = words[-1]["end"]

            # Chunk words into small punchy phrases (3 to 5 words max per card)
            chunk_size = 4
            for i in range(0, len(words), chunk_size):
                chunk = words[i:i + chunk_size]
                c_start = chunk[0]["start"]
                c_end = chunk[-1]["end"]

                # Generate karaoke string: {\k20}word {\k30}word
                karaoke_parts = []
                for w in chunk:
                    w_dur_cs = int((w["end"] - w["start"]) * 100) # centiseconds
                    karaoke_parts.append(f"{{\\k{max(10, w_dur_cs)}}}{w['word'].upper()}")

                line_text = " ".join(karaoke_parts)
                events.append(f"Dialogue: 0,{format_time(c_start)},{format_time(c_end)},{chosen_style},,0,0,0,,{line_text}")

        with open(output_ass_path, "w", encoding="utf-8") as f:
            f.write(header + "\n".join(events))

        return output_ass_path

    def render_subtitle_overlays(
        self,
        segments: List[Dict[str, Any]],
        output_dir: Path,
        start_offset: float = 0.0,
        clip_duration: float = 40.0
    ) -> List[Dict[str, Any]]:
        """
        Renders crisp transparent PNG overlay cards for each spoken word phrase
        with the current word active highlighted.
        Returns metadata for FFmpeg overlay filter chaining.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        cards = []
        font = get_font(size=56)

        # Style colors
        if self.style == "vice_city":
            normal_color = (255, 255, 255)
            active_color = (0, 240, 255)   # Vice City Cyan
            border_color = (0, 0, 0)
        else: # Hormozi
            normal_color = (255, 255, 255)
            active_color = (255, 230, 0)   # Electric Yellow
            border_color = (0, 0, 0)

        # Chunk all words into punchy 3-4 word cards
        all_words = []
        for seg in segments:
            for w in seg.get("words", []):
                if w["end"] >= start_offset and w["start"] <= start_offset + clip_duration:
                    all_words.append(w)

        chunk_size = 3
        card_idx = 0
        for i in range(0, len(all_words), chunk_size):
            chunk = all_words[i:i + chunk_size]
            if not chunk:
                continue

            # For each word in chunk, render a state where that word is active
            for active_idx, target_word in enumerate(chunk):
                w_start = max(0.0, target_word["start"] - start_offset)
                w_end = min(clip_duration, target_word["end"] - start_offset)

                if w_end <= w_start:
                    continue

                img = Image.new("RGBA", (TARGET_WIDTH, TARGET_HEIGHT), (0, 0, 0, 0))
                draw = ImageDraw.Draw(img)

                # Measure phrase total width to center it
                words_text = [w["word"].upper() for w in chunk]
                # Calculate spacing
                total_text = "  ".join(words_text)
                
                # Pillow textbbox
                bbox = draw.textbbox((0, 0), total_text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]

                # Position at y = 1280 (lower third, above player controls)
                x_start = (TARGET_WIDTH - text_width) // 2
                y_pos = 1260

                # Draw dark translucent rounded pill behind the text
                pad_x = 30
                pad_y = 16
                pill_box = [
                    x_start - pad_x,
                    y_pos - pad_y,
                    x_start + text_width + pad_x,
                    y_pos + text_height + pad_y + 8
                ]
                draw.rounded_rectangle(pill_box, radius=24, fill=(0, 0, 0, 160))

                # Draw words with stroke and active highlight
                curr_x = x_start
                for idx, word_str in enumerate(words_text):
                    color = active_color if idx == active_idx else normal_color
                    # Draw thick black stroke
                    draw.text(
                        (curr_x, y_pos),
                        word_str,
                        font=font,
                        fill=color,
                        stroke_width=6,
                        stroke_fill=border_color
                    )
                    word_bbox = draw.textbbox((0, 0), word_str + "  ", font=font)
                    curr_x += (word_bbox[2] - word_bbox[0])

                card_path = output_dir / f"sub_{card_idx:04d}.png"
                img.save(card_path, "PNG")

                cards.append({
                    "image_path": str(card_path),
                    "start": round(w_start, 2),
                    "end": round(w_end, 2)
                })
                card_idx += 1

        return cards

    def apply_subtitles_to_video(
        self,
        input_video: str,
        output_video: str,
        segments: List[Dict[str, Any]],
        start_offset: float,
        duration: float,
        encoder: str = "h264_videotoolbox"
    ) -> str:
        """
        Bakes dynamic subtitles onto the vertical video using transparent overlay sequence.
        """
        overlay_dir = TEMP_DIR / f"subs_{Path(input_video).stem}"
        cards = self.render_subtitle_overlays(
            segments=segments,
            output_dir=overlay_dir,
            start_offset=start_offset,
            clip_duration=duration
        )

        if not cards:
            logger.info("No subtitle cards to render. Keeping original video.")
            return input_video

        # We can burn subtitles using FFmpeg filter overlay chaining or an overlay concat script
        # For simplicity and speed: if more than 30 cards, build an FFmpeg filter script
        filter_inputs = []
        filter_chain = []
        last_stream = "[0:v]"

        cmd = ["ffmpeg", "-y", "-i", input_video]

        # Add image inputs
        for i, card in enumerate(cards):
            cmd.extend(["-i", card["image_path"]])
            out_stream = f"[v{i}]"
            start_t = card["start"]
            end_t = card["end"]
            filter_chain.append(
                f"{last_stream}[{i+1}:v]overlay=0:0:enable='between(t,{start_t},{end_t})'{out_stream}"
            )
            last_stream = out_stream

        filter_script = ";".join(filter_chain)
        cmd.extend(["-filter_complex", filter_script])
        cmd.extend(["-map", last_stream])
        cmd.extend(["-map", "0:a?"])

        if encoder == "h264_videotoolbox":
            cmd.extend(["-c:v", "h264_videotoolbox", "-b:v", "7M"])
        else:
            cmd.extend(["-c:v", "libx264", "-preset", "ultrafast", "-crf", "22"])

        cmd.extend(["-c:a", "copy", output_video])

        logger.info("Burning dynamic subtitle overlays with FFmpeg...")
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            logger.warning(f"Overlay failed ({res.stderr[:200]}), returning raw video.")
            return input_video

        return output_video

