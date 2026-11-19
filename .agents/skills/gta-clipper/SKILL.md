---
name: gta-clipper
description: >-
  Automated AI clipping pipeline for GTA 6 and gaming videos. Downloads YouTube or local videos,
  detects peak viral moments (action cuts, audio excitement, keyword hooks), reframes to 9:16
  vertical (Split, Blur, Crop), applies anti-copyright shields, renders Hormozi/Vice City karaoke subtitles,
  and generates multi-platform SEO packages for Instagram, YouTube Shorts, TikTok, and Rumble.
---

# GTA 6 Viral Clipper Skill

Use this skill whenever the user wants to:
1. Clip a YouTube video or local gaming gameplay into viral vertical shorts (9:16).
2. Launch or manage the local Web UI dashboard (`http://localhost:8000`).
3. Extract high-energy action scenes, dialogue hooks, or trailer highlights.
4. Apply transformative anti-copyright protection to avoid automated Content ID claims.
5. Generate high-converting captions, titles, and hashtags for Instagram Reels, YouTube Shorts, TikTok, or Rumble.

---

## Architecture & Tools Used

- **Video Ingestion**: `yt-dlp` (high-res 1080p stream & subtitle extraction).
- **Audio & Speech**: `faster-whisper` (word-level timestamps on Apple Silicon / CPU).
- **Virality Detection**: FFmpeg scene detection (`select='gt(scene,0.35)'`) + EBU R128 loudness energy analysis + hook heuristic.
- **Video Reframing & Rendering**: FFmpeg with `h264_videotoolbox` Apple Silicon hardware acceleration.
- **Kinetic Subtitles**: Alex Hormozi & Vice City neon karaoke overlays (Pillow + FFmpeg / Remotion React).
- **Transformative Anti-Copyright Shield**: Micro pitch variation, 1.03x tempo adjust, subtle cinematic color grading, and framing vignette.
- **Web UI & API**: FastAPI + SSE (Server-Sent Events) live terminal stream.

---

## How to Run

### 1. Launch the Localhost Web UI
To run the web dashboard on any port (default: 8000 or custom):
```bash
./start.sh 8000
# or
python3 server.py --port 8000
```
This automatically starts the FastAPI server and opens `http://localhost:8000` in the user's browser.

### 2. Autonomous CLI Execution
To clip a video directly from the command line:
```bash
source .venv/bin/activate
python clip_cli.py \
  --url "https://www.youtube.com/watch?v=QdBZY2fkU-0" \
  --clips 3 \
  --duration 40 \
  --layout split \
  --subtitles hormozi
```

Options:
- `--url`: YouTube link or path to local MP4/MKV file.
- `--clips`: Number of clips to extract (1 to 5).
- `--duration`: Target clip length in seconds (20 to 60).
- `--layout`: `split` (top GTA 6, bottom gameplay), `blur` (ambient blurred background), or `crop` (smart center crop).
- `--subtitles`: `hormozi` (yellow pop), `vice_city` (cyan/pink glow), or `clean` (white).
- `--no-anti-copyright`: Disable anti-copyright filters if raw original colors are needed.
- `--json`: Output structured JSON metadata for programmatic consumption.

### 3. File Outputs
- Generated clips are saved in `storage/exports/gta6_clip_<job_id>_<index>.mp4`.
- Intermediate files are in `storage/temp/`.
- Downloaded sources are in `storage/downloads/`.

