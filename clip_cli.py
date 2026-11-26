#!/usr/bin/env python3
"""
CLI entry point for GTA 6 Viral Clipper.
Allows clipping YouTube videos or local gaming recordings directly from terminal.
"""
import argparse
import sys
import json
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from backend.pipeline import ClippingPipeline

def main():
    parser = argparse.ArgumentParser(description="GTA 6 Viral Clipper CLI")
    parser.add_argument("--url", "-u", required=True, help="YouTube video URL or path to local video file")
    parser.add_argument("--clips", "-c", type=int, default=3, help="Number of clips to generate (default: 3)")
    parser.add_argument("--duration", "-d", type=float, default=40.0, help="Target clip duration in seconds (default: 40)")
    parser.add_argument("--layout", "-l", choices=["split", "blur", "crop"], default="split", help="9:16 vertical layout (default: split)")
    parser.add_argument("--no-anti-copyright", action="store_true", help="Disable anti-copyright filters")
    parser.add_argument("--subtitles", "-s", choices=["hormozi", "vice_city", "clean"], default="hormozi", help="Subtitle animation style")
    parser.add_argument("--section", choices=["full", "first_half", "middle", "last_half"], default="full", help="Video section: full, first_half (0-33%%), middle (33-67%%), last_half (67-100%%)")
    parser.add_argument("--preset", "-p", choices=["gta6_viral", "story_cutscene", "action_montage"], default="gta6_viral", help="Viral scoring preset (default: gta6_viral)")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")

    args = parser.parse_args()

    pipeline = ClippingPipeline()

    def on_progress(msg: str, pct: int):
        if not args.json:
            bar = ("#" * (pct // 5)).ljust(20, "-")
            sys.stdout.write(f"\r[{bar}] {pct}% | {msg[:55]}")
            sys.stdout.flush()

    try:
        res = pipeline.process(
            url_or_file=args.url,
            target_clips=args.clips,
            clip_duration=args.duration,
            layout=args.layout,
            enable_anti_copyright=not args.no_anti_copyright,
            subtitle_style=args.subtitles,
            video_section=args.section,
            preset=args.preset,
            progress_cb=on_progress
        )

        if not args.json:
            print("\n\n" + "=" * 60)
            print("🚀 GTA 6 VIRAL CLIPS READY FOR PUBLISHING!")
            print("=" * 60)
            for clip in res["clips"]:
                print(f"\n🎬 Clip #{clip['clip_id']} ({clip['duration']}s) - Virality Score: {clip['score']}%")
                print(f"📁 Path: {clip['file_path']}")
                print(f"🔥 Hook: {clip['hook_text']}")
                print(f"📸 IG Caption: {clip['seo']['instagram']['caption'][:80]}...")
                print(f"🔴 YT Title: {clip['seo']['youtube']['title']}")
            print("\n" + "=" * 60)
        else:
            print(json.dumps(res, indent=2))

    except Exception as e:
        print(f"\n❌ Error during clipping: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

