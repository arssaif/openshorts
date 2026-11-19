"""
AI Virality & Scene Analyzer:
Detects action peaks, audio energy, speech density, and scene transitions
to score moments that have the highest probability of going viral on Shorts/Reels/TikTok.
"""
import re
import json
import logging
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

VIRAL_KEYWORDS = {
    "gta 6": 3.0, "omg": 2.5, "insane": 2.5, "leak": 3.0, "look": 2.0,
    "secret": 2.5, "watch": 2.0, "crazy": 2.2, "trailer": 2.5, "reveal": 2.8,
    "vice city": 2.5, "lucia": 2.5, "jason": 2.5, "rockstar": 2.2, "heist": 2.0,
    "graphics": 2.2, "easter egg": 2.5, "fast": 1.8, "unbelievable": 2.5,
    "never": 2.0, "what": 1.5, "holy": 2.2, "car": 1.5, "police": 2.0
}

class ViralityAnalyzer:
    def __init__(self):
        pass

    def detect_scene_changes(self, video_path: str, max_duration: float = 600.0) -> List[float]:
        """
        Uses FFmpeg scene filter to detect timestamps of camera cuts and rapid action changes.
        """
        timestamps = []
        try:
            cmd = [
                "ffmpeg",
                "-t", str(max_duration),
                "-i", video_path,
                "-filter:v", "select='gt(scene,0.35)',showinfo",
                "-f", "null",
                "-"
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            # Parse showinfo output: pts_time: 12.345
            for match in re.finditer(r"pts_time:([0-9\.]+)", res.stderr):
                timestamps.append(float(match.group(1)))
        except Exception as e:
            logger.warning(f"Scene detection error: {e}")
        return timestamps

    def detect_audio_energy(self, video_path: str, max_duration: float = 600.0) -> List[Dict[str, float]]:
        """
        Measures momentary audio loudness (EBU R128) across time to find explosive audio peaks.
        """
        energy_points = []
        try:
            cmd = [
                "ffmpeg",
                "-t", str(max_duration),
                "-i", video_path,
                "-filter:a", "ebur128=metadata=1",
                "-f", "null",
                "-"
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            # Parse: [Parsed_ebur128_0 @ 0x...] t: 12.345   M: -18.2
            for match in re.finditer(r"t:\s*([0-9\.]+)\s+M:\s*([-\d\.]+)", res.stderr):
                t = float(match.group(1))
                loudness = float(match.group(2))
                # Convert LUFS (-70 to 0) to normalized energy (0.0 to 1.0)
                norm_energy = max(0.0, min(1.0, (loudness + 70.0) / 70.0))
                energy_points.append({"time": t, "energy": norm_energy})
        except Exception as e:
            logger.warning(f"Audio energy detection error: {e}")
        return energy_points

    def score_window(
        self,
        start_time: float,
        end_time: float,
        scene_timestamps: List[float],
        audio_energy: List[Dict[str, float]],
        transcript_segments: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculates the virality score (0-100) for a given time window.
        """
        duration = end_time - start_time
        if duration <= 0:
            return {"score": 0, "hook": "", "reasons": []}

        # 1. Action Density (scene changes per 10s)
        scenes_in_window = [t for t in scene_timestamps if start_time <= t <= end_time]
        scene_rate = len(scenes_in_window) / (duration / 10.0)
        action_score = min(30.0, scene_rate * 7.5) # Max 30 points

        # 2. Audio Peak & Average Energy
        energies = [p["energy"] for p in audio_energy if start_time <= p["time"] <= end_time]
        if energies:
            avg_energy = sum(energies) / len(energies)
            max_energy = max(energies)
            audio_score = (avg_energy * 0.4 + max_energy * 0.6) * 30.0 # Max 30 points
        else:
            audio_score = 15.0 # Neutral default

        # 3. Speech & Viral Keyword Detection
        segments_in_window = [
            s for s in transcript_segments
            if (s["start"] >= start_time and s["start"] < end_time) or
               (s["end"] > start_time and s["end"] <= end_time)
        ]
        
        full_text = " ".join([s.get("text", "") for s in segments_in_window]).lower()
        keyword_score = 0.0
        matched_keywords = []
        for kw, weight in VIRAL_KEYWORDS.items():
            if kw in full_text:
                keyword_score += weight * 4.0
                matched_keywords.append(kw)
        speech_score = min(20.0, keyword_score + (len(segments_in_window) * 2.0)) # Max 20 points

        # 4. First 3 Seconds Hook Score
        hook_window = start_time + 3.0
        hook_energies = [p["energy"] for p in audio_energy if start_time <= p["time"] <= hook_window]
        hook_scenes = [t for t in scene_timestamps if start_time <= t <= hook_window]
        hook_speech = [s for s in segments_in_window if s["start"] <= hook_window]

        hook_val = 0.0
        if hook_energies and max(hook_energies) > 0.65:
            hook_val += 8.0
        if hook_scenes:
            hook_val += 6.0
        if hook_speech:
            hook_val += 6.0
        hook_score = min(20.0, hook_val) # Max 20 points

        total_score = round(min(100.0, action_score + audio_score + speech_score + hook_score), 1)

        # Hook description for SEO/titles
        first_sentence = segments_in_window[0]["text"] if segments_in_window else "HIGH OCTANE GTA 6 ACTION"
        reasons = []
        if hook_score > 12:
            reasons.append("⚡ Explosive 3-second hook")
        if action_score > 18:
            reasons.append("🎬 Rapid action & scene cuts")
        if audio_score > 20:
            reasons.append("🔊 High-energy audio peaks")
        if matched_keywords:
            reasons.append(f"🔥 Viral keywords: {', '.join(matched_keywords[:3])}")

        return {
            "score": total_score,
            "action_score": round(action_score, 1),
            "audio_score": round(audio_score, 1),
            "speech_score": round(speech_score, 1),
            "hook_score": round(hook_score, 1),
            "hook_text": first_sentence,
            "reasons": reasons,
            "transcript": segments_in_window
        }

    def find_top_clips(
        self,
        video_path: str,
        total_duration: float,
        transcript_segments: List[Dict[str, Any]],
        target_clips: int = 3,
        clip_duration: float = 40.0,
        on_progress=None
    ) -> List[Dict[str, Any]]:
        """
        Scans video in sliding windows to find top virality peaks.
        """
        if on_progress:
            on_progress("Detecting scene cuts and high-octane camera angles...", 50)
        scene_timestamps = self.detect_scene_changes(video_path, max_duration=total_duration)

        if on_progress:
            on_progress("Analyzing audio loudness and excitement levels...", 55)
        audio_energy = self.detect_audio_energy(video_path, max_duration=total_duration)

        # Sliding window evaluation (step = 10s)
        step = 10.0
        candidate_windows = []
        curr = 0.0
        max_start = max(0.0, total_duration - clip_duration)

        if max_start == 0.0:
            # Video is shorter than target duration, return whole video
            meta = self.score_window(0.0, total_duration, scene_timestamps, audio_energy, transcript_segments)
            return [{
                "index": 1,
                "start": 0.0,
                "end": round(total_duration, 2),
                "duration": round(total_duration, 2),
                **meta
            }]

        while curr <= max_start:
            end = curr + clip_duration
            meta = self.score_window(curr, end, scene_timestamps, audio_energy, transcript_segments)
            candidate_windows.append({
                "start": round(curr, 2),
                "end": round(end, 2),
                "duration": round(clip_duration, 2),
                **meta
            })
            curr += step

        # Sort by score descending
        candidate_windows.sort(key=lambda x: x["score"], reverse=True)

        # Non-overlapping selection
        selected_clips = []
        for cand in candidate_windows:
            overlaps = False
            for sel in selected_clips:
                # Disallow overlap > 10s
                if not (cand["end"] <= sel["start"] + 10.0 or cand["start"] >= sel["end"] - 10.0):
                    overlaps = True
                    break
            if not overlaps:
                cand["index"] = len(selected_clips) + 1
                selected_clips.append(cand)
            if len(selected_clips) >= target_clips:
                break

        # Sort selected clips by chronological timeline
        selected_clips.sort(key=lambda x: x["start"])
        for i, c in enumerate(selected_clips):
            c["index"] = i + 1

        if on_progress:
            on_progress(f"Found {len(selected_clips)} viral moments with score up to {selected_clips[0]['score'] if selected_clips else 0}%!", 60)

        return selected_clips

