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
from typing import List, Dict, Any, Tuple, Optional

from backend.modules.comment_analyzer import CommentAnalyzer

logger = logging.getLogger(__name__)

VIRAL_KEYWORDS = {
    "gta 6": 3.0, "omg": 2.5, "insane": 2.5, "leak": 3.0, "look": 2.0,
    "secret": 2.5, "watch": 2.0, "crazy": 2.2, "trailer": 2.5, "reveal": 2.8,
    "vice city": 2.5, "lucia": 2.5, "jason": 2.5, "rockstar": 2.2, "heist": 2.0,
    "graphics": 2.2, "easter egg": 2.5, "fast": 1.8, "unbelievable": 2.5,
    "never": 2.0, "what": 1.5, "holy": 2.2, "car": 1.5, "police": 2.0
}

STORY_KEYWORDS = {
    "story": 2.5, "mission": 2.5, "cutscene": 3.0, "lucia": 2.8, "jason": 2.8,
    "vice city": 2.2, "character": 2.2, "trust": 2.5, "family": 2.5, "betray": 2.8,
    "money": 2.0, "love": 2.2, "plan": 2.2, "secret": 2.5, "truth": 2.5,
    "remember": 2.0, "listen": 2.2, "wait": 1.8, "tell": 2.0, "boss": 2.0,
    "talk": 2.0, "ending": 2.8, "reveal": 2.8, "spoiler": 2.5, "who": 1.5,
    "why": 1.5, "sorry": 2.0, "promise": 2.5, "deal": 2.2, "brother": 2.2, "sister": 2.2
}

ACTION_KEYWORDS = {
    "police": 2.5, "chase": 3.0, "shoot": 2.8, "crash": 2.8, "explosion": 3.0,
    "heist": 2.5, "car": 2.0, "fast": 2.2, "gun": 2.5, "fight": 2.5,
    "stunt": 2.8, "drift": 2.5, "boom": 2.8, "bam": 3.0, "kill": 2.5,
    "headshot": 3.0, "wreck": 2.5, "speed": 2.2, "insane": 2.2, "crazy": 2.0,
    "holy": 2.0, "wtf": 2.2, "run": 1.8, "escape": 2.5, "fire": 2.2,
    "cop": 2.2, "cops": 2.5, "siren": 2.5
}

class ViralityAnalyzer:
    def __init__(self):
        self.comment_analyzer = CommentAnalyzer()

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
                "-an",
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
                "-vn",
                "-filter:a", "ebur128=framelog=info",
                "-f", "null",
                "-"
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            # Parse: [Parsed_ebur128_0 @ 0x...] t: 0.399977   TARGET:-23 LUFS    M: -31.6 ...
            for match in re.finditer(r"t:\s*([0-9\.]+).*?\bM:\s*([-\d\.]+)", res.stderr):
                t = float(match.group(1))
                loudness = float(match.group(2))
                if loudness < -100.0:
                    norm_energy = 0.0
                else:
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
        transcript_segments: List[Dict[str, Any]],
        timestamp_comments: Optional[List[Dict[str, Any]]] = None,
        section_offset: float = 0.0,
        preset: str = "gta6_viral",
        audio_baseline: float = 0.5,
        audio_p90: float = 0.75
    ) -> Dict[str, Any]:
        """
        Calculates the virality score (0-100) for a given time window,
        incorporating preset-specific weighting across scene changes, audio loudness,
        speech keywords, and audience comment excitement.
        """
        duration = end_time - start_time
        if duration <= 0:
            return {"score": 0.0, "raw_score": 0.0, "hook_text": "", "reasons": [], "transcript": []}

        scenes_in_window = [t for t in scene_timestamps if start_time <= t <= end_time]
        scene_rate = len(scenes_in_window) / (duration / 10.0)
        energies = [p["energy"] for p in audio_energy if start_time <= p["time"] <= end_time]

        segments_in_window = [
            s for s in transcript_segments
            if (s["start"] >= start_time and s["start"] < end_time) or
               (s["end"] > start_time and s["end"] <= end_time)
        ]

        full_text = " ".join([s.get("text", "") for s in segments_in_window]).lower()
        word_count = len(full_text.split())

        comment_score = 0.0
        comment_reasons = []
        highlight_quote = ""
        if timestamp_comments:
            c_data = self.comment_analyzer.score_window(
                start_time, end_time, timestamp_comments, section_offset=section_offset
            )
            comment_score = c_data.get("score", 0.0)
            comment_reasons = c_data.get("reasons", [])
            highlight_quote = c_data.get("highlight_quote", "")

        matched_keywords: List[str] = []
        reasons: List[str] = []
        if comment_reasons:
            reasons.extend(comment_reasons)

        if preset == "story_cutscene":
            if word_count == 0:
                speech_score = 0.0
            else:
                story_kw_pts = 0.0
                for kw, weight in STORY_KEYWORDS.items():
                    if kw in full_text:
                        story_kw_pts += weight * 3.0
                        matched_keywords.append(kw)
                dialogue_pts = min(25.0, (word_count / 3.5) + (len(segments_in_window) * 1.5))
                speech_score = min(45.0, dialogue_pts + story_kw_pts)

            n_cuts = len(scenes_in_window)
            if 1 <= n_cuts <= 5:
                action_score = 15.0
            elif n_cuts == 0:
                action_score = 8.0
            else:
                action_score = max(3.0, 15.0 - (n_cuts - 5) * 2.0)

            if energies:
                avg_e = sum(energies) / len(energies)
                deviation = abs(avg_e - audio_baseline)
                spike_ratio = sum(1 for e in energies if e > audio_p90) / len(energies)
                audio_score = max(3.0, min(15.0, 15.0 - (deviation * 20.0) - (spike_ratio * 10.0)))
            else:
                audio_score = 7.5

            hook_speech_5s = [s for s in segments_in_window if s["start"] <= start_time + 5.0]
            hook_scenes_5s = [t for t in scene_timestamps if start_time <= t <= start_time + 5.0]
            hook_val = (10.0 if hook_speech_5s else 0.0) + (5.0 if 1 <= len(hook_scenes_5s) <= 2 else 0.0)
            hook_score = min(15.0, hook_val)

            comment_cap = min(20.0, comment_score * (20.0 / 30.0))
            base_sum = speech_score + action_score + audio_score + hook_score
            raw_score = (base_sum + comment_cap) if timestamp_comments else (base_sum * 1.15)

            if speech_score >= 20.0:
                reasons.append("🌴 Story & dialogue focus")

        elif preset == "action_montage":
            burst_cuts = sum(
                1 for i in range(1, len(scenes_in_window))
                if scenes_in_window[i] - scenes_in_window[i - 1] <= 3.0
            )
            action_score = min(45.0, scene_rate * 10.0 + burst_cuts * 2.5)

            if energies:
                max_e = max(energies)
                min_e = min(energies)
                p90_frac = sum(1 for e in energies if e >= audio_p90) / len(energies)
                dyn_range = max(0.0, max_e - min_e)
                audio_score = min(35.0, (max_e * 12.0) + (p90_frac * 45.0) + (dyn_range * 25.0))
            else:
                audio_score = 10.0

            act_kw_pts = 0.0
            for kw, weight in ACTION_KEYWORDS.items():
                if kw in full_text:
                    act_kw_pts += weight * 3.0
                    matched_keywords.append(kw)
            speech_score = min(10.0, act_kw_pts)
            dialogue_penalty = 5.0 if (word_count > 45 and len(scenes_in_window) <= 1) else 0.0

            hook_energies = [p["energy"] for p in audio_energy if start_time <= p["time"] <= start_time + 3.0]
            hook_scenes = [t for t in scene_timestamps if start_time <= t <= start_time + 3.0]
            hook_val = (8.0 if hook_scenes else 0.0) + (7.0 if (hook_energies and max(hook_energies) >= audio_p90) else 0.0)
            hook_score = min(15.0, hook_val)

            comment_cap = min(20.0, comment_score * (20.0 / 30.0))
            base_sum = max(0.0, action_score + audio_score + speech_score + hook_score - dialogue_penalty)
            raw_score = (base_sum + comment_cap) if timestamp_comments else (base_sum * 1.15)

            if action_score >= 20.0 or audio_score >= 22.0:
                reasons.append("🚗 High-intensity gameplay action")

        else:  # "gta6_viral" balanced default
            action_score = min(25.0, scene_rate * 6.5)

            if energies:
                avg_e = sum(energies) / len(energies)
                max_e = max(energies)
                rel_spike = max(0.0, max_e - audio_baseline)
                audio_score = min(25.0, (avg_e * 0.4 + max_e * 0.6) * 20.0 + rel_spike * 20.0)
            else:
                audio_score = 12.0

            keyword_score = 0.0
            for kw, weight in VIRAL_KEYWORDS.items():
                if kw in full_text:
                    keyword_score += weight * 3.0
                    matched_keywords.append(kw)
            speech_score = min(15.0, keyword_score + (len(segments_in_window) * 1.5))

            hook_window = start_time + 3.0
            hook_energies = [p["energy"] for p in audio_energy if start_time <= p["time"] <= hook_window]
            hook_scenes = [t for t in scene_timestamps if start_time <= t <= hook_window]
            hook_speech = [s for s in segments_in_window if s["start"] <= hook_window]

            hook_val = 0.0
            if hook_energies and max(hook_energies) >= max(0.65, audio_p90):
                hook_val += 6.0
            if hook_scenes:
                hook_val += 5.0
            if hook_speech:
                hook_val += 4.0
            hook_score = min(15.0, hook_val)

            if timestamp_comments:
                raw_score = action_score + audio_score + speech_score + hook_score + min(25.0, comment_score)
            else:
                raw_score = (action_score + audio_score + speech_score + hook_score) * 1.25

        total_score = round(min(100.0, max(0.0, raw_score)), 1)

        # Hook description for SEO/titles
        first_sentence = segments_in_window[0]["text"] if segments_in_window else (highlight_quote or "HIGH OCTANE GTA 6 ACTION")
        if hook_score > 9:
            reasons.append("⚡ Explosive 3-second opening hook")
        if action_score > 14:
            reasons.append("🎬 Rapid action & scene cuts")
        if audio_score > 16:
            reasons.append("🔊 High-energy audio peaks")
        if matched_keywords:
            reasons.append(f"🔥 Viral keywords: {', '.join(matched_keywords[:3])}")

        return {
            "score": total_score,
            "raw_score": round(raw_score, 3),
            "action_score": round(action_score, 1),
            "audio_score": round(audio_score, 1),
            "speech_score": round(speech_score, 1),
            "hook_score": round(hook_score, 1),
            "comment_score": round(comment_score, 1),
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
        timestamp_comments: Optional[List[Dict[str, Any]]] = None,
        section_offset: float = 0.0,
        preset: str = "gta6_viral",
        on_progress=None
    ) -> List[Dict[str, Any]]:
        """
        Scans video in sliding windows to find top virality peaks for the chosen preset.
        """
        if on_progress:
            on_progress("Detecting scene cuts and high-octane camera angles...", 50)
        scene_timestamps = self.detect_scene_changes(video_path, max_duration=total_duration)

        if on_progress:
            on_progress("Analyzing audio loudness and excitement levels...", 53)
        audio_energy = self.detect_audio_energy(video_path, max_duration=total_duration)

        if audio_energy:
            sorted_e = sorted(p["energy"] for p in audio_energy)
            n_e = len(sorted_e)
            audio_baseline = sorted_e[n_e // 2]
            audio_p90 = sorted_e[min(n_e - 1, int(n_e * 0.90))]
        else:
            audio_baseline = 0.5
            audio_p90 = 0.75

        if timestamp_comments and on_progress:
            on_progress(f"Correlating {len(timestamp_comments)} viewer comments & excitement hotspots...", 56)

        # Sliding window evaluation (step = 10s)
        step = 10.0
        candidate_windows = []
        curr = 0.0
        max_start = max(0.0, total_duration - clip_duration)

        if max_start == 0.0:
            # Video is shorter than target duration, return whole video
            meta = self.score_window(
                0.0, total_duration, scene_timestamps, audio_energy,
                transcript_segments, timestamp_comments,
                section_offset=section_offset, preset=preset,
                audio_baseline=audio_baseline, audio_p90=audio_p90
            )
            return [{
                "index": 1,
                "start": 0.0,
                "end": round(total_duration, 2),
                "duration": round(total_duration, 2),
                **meta
            }]

        while curr <= max_start:
            end = curr + clip_duration
            meta = self.score_window(
                curr, end, scene_timestamps, audio_energy,
                transcript_segments, timestamp_comments,
                section_offset=section_offset, preset=preset,
                audio_baseline=audio_baseline, audio_p90=audio_p90
            )
            candidate_windows.append({
                "start": round(curr, 2),
                "end": round(end, 2),
                "duration": round(clip_duration, 2),
                **meta
            })
            curr += step

        # Sort by uncapped raw_score descending so 100.0 ties preserve true ranking
        candidate_windows.sort(key=lambda x: x["raw_score"], reverse=True)

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
            top_score = max((c["score"] for c in selected_clips), default=0)
            on_progress(f"Found {len(selected_clips)} {preset} moments with score up to {top_score}%!", 60)

        return selected_clips

