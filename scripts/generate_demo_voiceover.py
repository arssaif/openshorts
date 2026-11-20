"""
Generates local AI voiceover for OpenShorts demo using Kokoro TTS (82M ONNX model)
and composites it with game audio and Playwright recorded video into assets/demo.mp4.
"""
import os
import subprocess
from pathlib import Path
import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = ROOT / "storage" / "models"
TEMP_DIR = ROOT / "storage" / "temp"
EXPORTS_DIR = ROOT / "storage" / "exports"
ASSETS_DIR = ROOT / "assets"

MODEL_PATH = MODELS_DIR / "kokoro-v1.0.onnx"
VOICES_PATH = MODELS_DIR / "voices-v1.0.bin"
VIDEO_WEBM = list((TEMP_DIR / "playwright_recordings").glob("*.webm"))[0]
CLIP_MP4 = EXPORTS_DIR / "gta6_clip_9e312eb2_1.mp4"
OUTPUT_MP4 = ASSETS_DIR / "demo.mp4"
OUTPUT_GIF = ASSETS_DIR / "demo.gif"

TARGET_SR = 44100
TOTAL_DUR = 31.96

def resample_to_sr(file_path, target_sr=44100):
    cmd = [
        "ffmpeg", "-y", "-i", str(file_path),
        "-ar", str(target_sr),
        "-ac", "2",
        "-f", "wav",
        "-"
    ]
    proc = subprocess.run(cmd, capture_output=True, check=True)
    import io
    data, _ = sf.read(io.BytesIO(proc.stdout))
    return data

def main():
    print("🎙️ Initializing Kokoro TTS (82M ONNX)...")
    kokoro = Kokoro(str(MODEL_PATH), str(VOICES_PATH))

    voice_lines = [
        ("line1", "Welcome to OpenShorts AI, the autonomous video clipper for gaming and viral content.", 0.6, 1.4),
        ("line2", "Customize vertical nine sixteen layouts, karaoke subtitle styles, and focus sections.", 6.0, 1.4),
        ("line3", "Our AI scans rapid scene cuts, loudness spikes, and audience excitement in comments.", 11.2, 1.4),
        ("line4", "Extract sixty F P S viral moments with transformative anti copyright protection.", 16.2, 1.3),
        ("line5", "Get platform-optimized titles, hashtags, and one-click clean captions ready to post.", 22.8, 1.4)
    ]

    total_samples = int(TARGET_SR * TOTAL_DUR)
    master = np.zeros((total_samples, 2), dtype=np.float32)

    for name, text, start_sec, vol in voice_lines:
        print(f"🗣️ Generating Kokoro TTS: '{text[:40]}...' at t={start_sec}s")
        samples, sr = kokoro.create(text, voice="am_adam", speed=1.12)
        wav_path = TEMP_DIR / f"{name}.wav"
        sf.write(str(wav_path), samples, sr)

        audio = resample_to_sr(wav_path, TARGET_SR) * vol
        start_idx = int(start_sec * TARGET_SR)
        end_idx = min(total_samples, start_idx + len(audio))
        actual_len = end_idx - start_idx
        master[start_idx:end_idx] += audio[:actual_len]

    # Mix in Game Audio from 15.4s
    print("🎮 Compositing gameplay sound effects with voice ducking...")
    game_audio = resample_to_sr(CLIP_MP4, TARGET_SR)
    game_start_idx = int(15.4 * TARGET_SR)
    game_end_idx = min(total_samples, game_start_idx + len(game_audio))
    game_len = game_end_idx - game_start_idx

    env = np.ones(game_len, dtype=np.float32)
    for i in range(game_len):
        t = 15.4 + (i / TARGET_SR)
        if t < 21.5:
            env[i] = 0.45
        elif t < 22.8:
            env[i] = 0.85
        elif t < 27.6:
            env[i] = 0.40
        else:
            env[i] = 0.85

    master[game_start_idx:game_end_idx] += game_audio[:game_len] * env[:, None]

    # Normalize audio
    peak = np.max(np.abs(master))
    if peak > 0.95:
        master = master * (0.95 / peak)

    master_wav = TEMP_DIR / "demo_master_audio.wav"
    sf.write(str(master_wav), master, TARGET_SR)

    # Multiplex to MP4
    print("🎬 Rendering final demo.mp4...")
    subprocess.run([
        "ffmpeg", "-y",
        "-i", str(VIDEO_WEBM),
        "-i", str(master_wav),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        str(OUTPUT_MP4)
    ], check=True)

    # Render optimized GIF
    print("🖼️ Generating demo.gif...")
    palette = TEMP_DIR / "palette.png"
    subprocess.run([
        "ffmpeg", "-y", "-i", str(OUTPUT_MP4),
        "-vf", "fps=12,scale=800:-1:flags=lanczos,palettegen=stats_mode=diff",
        str(palette)
    ], check=True)
    subprocess.run([
        "ffmpeg", "-y", "-i", str(OUTPUT_MP4), "-i", str(palette),
        "-filter_complex", "fps=12,scale=800:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle",
        str(OUTPUT_GIF)
    ], check=True)

    print("✅ All demo assets generated successfully with Kokoro TTS voiceover!")

if __name__ == "__main__":
    main()

