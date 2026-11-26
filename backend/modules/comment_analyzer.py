"""
Comment and Discussion Virality Analyzer:
Extracts YouTube comments & live chat discussions to find moments with peak audience excitement,
timestamp references, and viral keywords ('bam', 'amazing', 'cool', 'insane', 'clutch', etc.).
"""
import re
import math
import sys
import shutil
import logging
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

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

# Excitement words prioritized for gaming & live gameplay reactions
EXCITEMENT_KEYWORDS = {
    # User requested explicit keywords
    "bam": 4.0,
    "amazing": 3.5,
    "cool": 3.0,
    # High-intensity gaming & chat reaction words
    "insane": 3.5,
    "crazy": 3.0,
    "omg": 3.0,
    "wtf": 3.0,
    "holy": 3.0,
    "pog": 3.5,
    "clutch": 4.0,
    "hype": 3.5,
    "fire": 3.0,
    "epic": 3.5,
    "sick": 3.0,
    "unreal": 3.5,
    "goat": 3.5,
    "headshot": 3.5,
    "stunt": 3.0,
    "jump": 2.5,
    "boss": 3.0,
    "win": 2.5,
    "lol": 2.0,
    "lmao": 2.5,
    "cooked": 3.0,
    "no way": 3.5,
    "screaming": 3.0,
    "reaction": 2.5,
    "best part": 4.0,
    "favorite": 3.0,
    "died": 2.5,
    "laughed": 2.5,
    "destroyed": 3.0,
    "legendary": 3.5
}

TIMESTAMP_REGEX = re.compile(r'\b(?:(\d{1,2}):)?(\d{1,2}):(\d{2})\b')

class CommentAnalyzer:
    def __init__(self):
        pass

    def fetch_comments_for_url(self, url: str, max_comments: int = 150) -> List[Dict[str, Any]]:
        """
        Fetches comments from a YouTube video URL using yt-dlp.
        """
        if not url or not url.startswith("http"):
            return []

        try:
            ytdlp_bin = get_ytdlp_cmd()
            cmd = [
                ytdlp_bin,
                "--extractor-args", f"youtube:player_client=android;max_comments={max_comments}",
                "--dump-json",
                "--get-comments",
                "--skip-download",
                url
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            if res.returncode == 0 and res.stdout.strip():
                data = json.loads(res.stdout)
                comments = data.get("comments", [])
                logger.info(f"Fetched {len(comments)} YouTube comments for virality analysis.")
                return comments
        except subprocess.TimeoutExpired:
            logger.warning("Fetching comments timed out after 20s, proceeding without comments.")
        except Exception as e:
            logger.warning(f"Could not fetch YouTube comments: {e}")

        return []

    def parse_timestamp_comments(self, raw_comments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Parses raw comments to extract timestamp references and calculate discussion excitement scores.
        """
        parsed_points = []
        if not raw_comments:
            return parsed_points

        for c in raw_comments:
            text = c.get("text", "")
            if not text:
                continue

            lower_text = text.lower()
            likes = int(c.get("like_count") or 0)
            author = c.get("author", "Viewer")

            # Check for timestamp mentions (ignore chapter-list / TOC comments with > 5 timestamps)
            matches = list(TIMESTAMP_REGEX.finditer(text))
            if not matches or len(matches) > 5:
                continue

            # Detect excited reaction words
            matched_words = []
            excitement_boost = 0.0
            for word, weight in EXCITEMENT_KEYWORDS.items():
                if re.search(r'\b' + re.escape(word) + r'\b', lower_text):
                    matched_words.append(word)
                    excitement_boost += weight

            # Likes weighting (diminishing returns via log scale)
            like_multiplier = 1.0 + min(4.0, math.log10(1 + likes)) if likes > 0 else 1.0

            # Base score per timestamp mention
            base_mention_score = 6.0 + excitement_boost
            total_comment_weight = base_mention_score * like_multiplier

            for m in matches:
                h_str, m_str, s_str = m.groups()
                hours = int(h_str) if h_str else 0
                minutes = int(m_str)
                seconds = int(s_str)
                timestamp_sec = hours * 3600 + minutes * 60 + seconds

                parsed_points.append({
                    "time": float(timestamp_sec),
                    "score": round(total_comment_weight, 2),
                    "text": text.strip()[:140],
                    "matched_words": matched_words,
                    "author": author,
                    "likes": likes
                })

        logger.info(f"Identified {len(parsed_points)} timestamp discussion markers in comments.")
        return parsed_points

    def score_window(
        self,
        start_time: float,
        end_time: float,
        timestamp_comments: List[Dict[str, Any]],
        section_offset: float = 0.0
    ) -> Dict[str, Any]:
        """
        Scores a candidate clip window [start_time, end_time] based on comment excitement.
        section_offset: if video was downloaded with an offset (e.g. from 2h00m),
        we map local file window [start, end] to absolute timeline [start + offset, end + offset].
        """
        if not timestamp_comments:
            return {
                "score": 0.0,
                "mentions": 0,
                "matched_words": [],
                "highlight_quote": "",
                "reasons": []
            }

        abs_start = start_time + section_offset
        abs_end = end_time + section_offset
        # Tolerant margin: comments often mark the start of the action or a few seconds early/late
        search_start = max(0.0, abs_start - 6.0)
        search_end = abs_end + 6.0

        hits = [
            c for c in timestamp_comments
            if search_start <= c["time"] <= search_end
        ]

        if not hits:
            return {
                "score": 0.0,
                "mentions": 0,
                "matched_words": [],
                "highlight_quote": "",
                "reasons": []
            }

        # Sum weighted scores
        raw_sum = sum(h["score"] for h in hits)
        # Cluster consensus bonus: multiple distinct comments discussing this scene = viral gold
        cluster_bonus = 1.0 + (min(5, len(hits) - 1) * 0.35)
        # Normalize to 0-30 points scale
        normalized_score = min(30.0, (raw_sum * cluster_bonus) / 2.5)

        # Collect unique excited words across hits
        all_words = []
        for h in hits:
            all_words.extend(h["matched_words"])
        unique_words = sorted(list(set(all_words)), key=lambda w: EXCITEMENT_KEYWORDS.get(w, 1.0), reverse=True)

        # Best quote (highest scored comment)
        hits_sorted = sorted(hits, key=lambda x: x["score"], reverse=True)
        best_quote = hits_sorted[0]["text"]

        reasons = []
        if len(hits) >= 3:
            reasons.append(f"💬 Crowd Consensus: {len(hits)} timestamp comments discussing this scene")
        elif len(hits) >= 1:
            reasons.append(f"💬 High Comment Buzz ({len(hits)} mentions)")

        if unique_words:
            top_words = unique_words[:3]
            reasons.append(f"🔥 Comment Excitement: {', '.join(top_words)}")

        return {
            "score": round(normalized_score, 1),
            "mentions": len(hits),
            "matched_words": unique_words,
            "highlight_quote": best_quote,
            "reasons": reasons
        }

    def find_peak_discussion_clusters(
        self,
        timestamp_comments: List[Dict[str, Any]],
        min_time: float,
        max_time: float,
        cluster_window: float = 60.0
    ) -> List[Dict[str, Any]]:
        """
        Finds clusters where comments are densely concentrated within [min_time, max_time].
        Useful for long gameplay streams to pick the best section window.
        """
        valid_comments = [c for c in timestamp_comments if min_time <= c["time"] <= max_time]
        if not valid_comments:
            return []

        clusters = []
        valid_comments.sort(key=lambda x: x["time"])
        for c in valid_comments:
            center = c["time"]
            window_hits = [
                h for h in valid_comments
                if abs(h["time"] - center) <= cluster_window / 2.0
            ]
            total_score = sum(h["score"] for h in window_hits)
            clusters.append({
                "center_time": center,
                "count": len(window_hits),
                "total_score": total_score,
                "sample_text": c["text"]
            })

        clusters.sort(key=lambda x: x["total_score"], reverse=True)
        return clusters

