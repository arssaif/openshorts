"""
Transcriber module: Extracts word-level timestamped transcripts using
either YouTube captions (instant) or faster-whisper (local AI).
"""
import re
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class AudioTranscriber:
    def __init__(self, model_size: str = "base"):
        self.model_size = model_size
        self._whisper_model = None

    def _get_whisper(self):
        if self._whisper_model is None:
            try:
                from faster_whisper import WhisperModel
                # Run on CPU with INT8 quantization, blazing fast on Apple Silicon
                self._whisper_model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
            except Exception as e:
                logger.error(f"Failed to load faster-whisper: {e}")
                self._whisper_model = False
        return self._whisper_model

    def parse_vtt(self, vtt_path: str) -> List[Dict[str, Any]]:
        """Parses WebVTT subtitles into structured segments and words."""
        segments = []
        try:
            with open(vtt_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Pattern for timestamp line: 00:00:01.000 --> 00:00:04.000
            pattern = re.compile(r"(\d{2}:\d{2}:\d{2}\.\d{3}|\d{2}:\d{2}\.\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}\.\d{3}|\d{2}:\d{2}\.\d{3})\n(.*?)(?=\n\n|\Z)", re.DOTALL)
            
            def to_seconds(t_str: str) -> float:
                parts = t_str.split(":")
                if len(parts) == 3:
                    h, m, s = parts
                    return int(h) * 3600 + int(m) * 60 + float(s)
                elif len(parts) == 2:
                    m, s = parts
                    return int(m) * 60 + float(s)
                return 0.0

            for match in pattern.finditer(content):
                start_str, end_str, text_block = match.groups()
                start = to_seconds(start_str)
                end = to_seconds(end_str)
                # Clean HTML tags like <c> </c>
                clean_text = re.sub(r"<[^>]+>", "", text_block).strip()
                if clean_text:
                    words_raw = clean_text.split()
                    w_count = len(words_raw)
                    duration = max(0.1, end - start)
                    w_duration = duration / max(1, w_count)
                    
                    word_objs = []
                    for i, w in enumerate(words_raw):
                        w_start = start + i * w_duration
                        w_end = w_start + w_duration
                        word_objs.append({
                            "word": w,
                            "start": round(w_start, 2),
                            "end": round(w_end, 2)
                        })
                    
                    segments.append({
                        "start": round(start, 2),
                        "end": round(end, 2),
                        "text": clean_text,
                        "words": word_objs
                    })
        except Exception as e:
            logger.warning(f"Error parsing VTT: {e}")
        return segments

    def transcribe_audio(self, audio_or_video_path: str, subtitle_path: Optional[str] = None, on_progress=None) -> List[Dict[str, Any]]:
        """
        Transcribes audio with word-level timestamps.
        Tries pre-existing subtitle_path first, then faster-whisper.
        """
        if subtitle_path and Path(subtitle_path).exists():
            if on_progress:
                on_progress("Parsing high-accuracy native transcript...", 40)
            segments = self.parse_vtt(subtitle_path)
            if segments:
                return segments

        # Fallback to local Whisper
        if on_progress:
            on_progress("Transcribing audio with faster-whisper (word timestamps)...", 45)

        whisper = self._get_whisper()
        if not whisper:
            logger.warning("Whisper not available, returning empty transcript.")
            return []

        segments_out = []
        try:
            whisper_segments, info = whisper.transcribe(
                audio_or_video_path,
                beam_size=5,
                word_timestamps=True,
                vad_filter=True, # Voice Activity Detection
                vad_parameters=dict(min_silence_duration_ms=500)
            )

            for seg in whisper_segments:
                words = []
                if seg.words:
                    for w in seg.words:
                        words.append({
                            "word": w.word.strip(),
                            "start": round(w.start, 2),
                            "end": round(w.end, 2),
                            "probability": round(w.probability, 2)
                        })
                segments_out.append({
                    "start": round(seg.start, 2),
                    "end": round(seg.end, 2),
                    "text": seg.text.strip(),
                    "words": words
                })
        except Exception as e:
            logger.error(f"Whisper transcription failed: {e}")

        return segments_out

