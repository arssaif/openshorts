import os
import sys
import time
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
RECORDINGS_DIR = ROOT / "storage" / "temp" / "playwright_recordings"
RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)

def record_demo():
    print("🎬 Starting Playwright browser demo recording...")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--autoplay-policy=no-user-gesture-required",
            ]
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            record_video_dir=str(RECORDINGS_DIR),
            record_video_size={"width": 1280, "height": 800}
        )
        page = context.new_page()

        print("🌐 Navigating to http://localhost:8097/...")
        page.goto("http://localhost:8097/", wait_until="networkidle")
        time.sleep(1.5)

        # Hover and click Presets
        print("🖱️ Interacting with Presets...")
        page.hover("[data-preset='story_cutscene']")
        time.sleep(0.5)
        page.click("[data-preset='story_cutscene']")
        time.sleep(0.7)

        page.hover("[data-preset='action_montage']")
        time.sleep(0.5)
        page.click("[data-preset='action_montage']")
        time.sleep(0.7)

        page.hover("[data-preset='gta6_viral']")
        time.sleep(0.5)
        page.click("[data-preset='gta6_viral']")
        time.sleep(0.8)

        # Interacting with 9:16 layouts
        print("🖱️ Interacting with 9:16 layouts...")
        page.hover("input[value='blur']")
        time.sleep(0.4)
        page.click("input[value='blur']")
        time.sleep(0.6)

        page.hover("input[value='crop']")
        time.sleep(0.4)
        page.click("input[value='crop']")
        time.sleep(0.6)

        page.hover("input[value='split']")
        time.sleep(0.4)
        page.click("input[value='split']")
        time.sleep(0.8)

        # Interacting with Subtitle Styles
        print("🖱️ Interacting with Subtitle styles...")
        page.hover("input[value='vice_city']")
        time.sleep(0.4)
        page.click("input[value='vice_city']")
        time.sleep(0.6)

        page.hover("input[value='hormozi']")
        time.sleep(0.4)
        page.click("input[value='hormozi']")
        time.sleep(0.8)

        # Click Generate button
        print("⚡ Clicking 'Generate Viral Clips Now'...")
        page.hover("#generate-btn")
        time.sleep(0.4)

        start_click_time = time.time()
        # Trigger progress animation in UI
        page.evaluate("""
            () => {
                const progressCard = document.getElementById('progress-card');
                const resultsSection = document.getElementById('results-section');
                const progressFill = document.getElementById('progress-fill');
                const progressPct = document.getElementById('progress-pct');
                const progressTitle = document.getElementById('progress-status-title');
                const progressDetail = document.getElementById('progress-status-detail');
                const terminalBody = document.getElementById('terminal-body');
                const generateBtn = document.getElementById('generate-btn');

                progressCard.style.display = 'block';
                resultsSection.style.display = 'none';
                generateBtn.disabled = true;
                generateBtn.style.opacity = '0.5';

                function log(msg, cls='info') {
                    const line = document.createElement('div');
                    line.className = 'log-line ' + cls;
                    line.textContent = '[' + new Date().toLocaleTimeString() + '] ' + msg;
                    terminalBody.appendChild(line);
                    terminalBody.scrollTop = terminalBody.scrollHeight;
                }

                window.__demoTimers = [];
                const steps = [
                    { pct: 15, msg: 'Loading GTA 6 4K video stream & audio track...', delay: 200 },
                    { pct: 35, msg: 'faster-whisper: Extracted word timestamps with Apple Silicon NEON...', delay: 800 },
                    { pct: 55, msg: 'AI Virality Engine: Loudness peak (+9.2 dB) & 4 rapid scene cuts detected...', delay: 1500 },
                    { pct: 75, msg: 'FFmpeg VideoToolbox: Rendered 9:16 Viral Split with Anti-Copyright Shield...', delay: 2200 },
                    { pct: 90, msg: 'Subtitle Engine: Baked kinetic Alex Hormozi animated karaoke typography...', delay: 2800 },
                    { pct: 100, msg: 'All clips ready for multi-platform publishing! 🎉', delay: 3400 }
                ];

                steps.forEach(s => {
                    const t = setTimeout(() => {
                        progressFill.style.width = s.pct + '%';
                        progressPct.textContent = s.pct + '%';
                        progressTitle.textContent = s.pct === 100 ? 'Processing Complete!' : 'Creating Viral Clips...';
                        progressDetail.textContent = s.msg;
                        log('[' + s.pct + '%] ' + s.msg, s.pct === 100 ? 'success' : 'info');

                        if (s.pct === 100) {
                            generateBtn.disabled = false;
                            generateBtn.style.opacity = '1';
                        }
                    }, s.delay);
                    window.__demoTimers.push(t);
                });
            }
        """)

        # Wait for simulated progress
        time.sleep(3.6)

        # Now render the real clips into results section
        print("🎬 Rendering generated clips in dashboard...")
        page.evaluate("""
            () => {
                const resultsSection = document.getElementById('results-section');
                const clipsGrid = document.getElementById('clips-grid');
                resultsSection.style.display = 'block';
                clipsGrid.innerHTML = '';

                const demoClips = [
                    {
                        clip_id: '9e312eb2_1',
                        filename: 'gta6_clip_9e312eb2_1.mp4',
                        url: '/api/clips/gta6_clip_9e312eb2_1.mp4',
                        duration: 40,
                        score: 96,
                        reasons: ['🔥 Loudness Spike (+8.4 dB)', '⚡ High Action Scene Cut', '🌴 Vice City Hook Detected'],
                        seo: {
                            instagram: {
                                caption: "Wait until you notice this in GTA 6… 🤯🌴\\n\\nRockstar Games is taking Vice City to a whole new level of realism and chaos! Drop a comment if you're ready for 2025! 👇\\n\\n⚡ Follow for daily GTA 6 leaks & clips!\\n#GTA6 #GrandTheftAuto6 #ViceCity #GamingReels #GTA6Trailer"
                            },
                            youtube: {
                                title: "GTA 6 Did WHAT?! 🤯 (Secret Gameplay Reveal) #shorts",
                                description: "🔥 Watch this crazy GTA 6 moment! Lucia and Jason in Vice City.\\n\\n🎮 Game: Grand Theft Auto VI (Rockstar Games)\\n📈 Virality Peak: 96% Action Density\\n#GTA6 #GamingShorts #RockstarGames #ViceCity #Shorts",
                                tags: "gta 6, grand theft auto 6, gta vi, gta 6 gameplay, gta 6 clips, vice city, rockstar games, viral shorts"
                            },
                            tiktok: {
                                caption: "Rockstar really put this in GTA 6?! 💀🔥 The attention to detail is actually terrifying. #gta6 #grandtheftauto #vicecity #gaming #gamingontiktok",
                                sound_tip: "Pair with 'Vice City Synthwave 80s' trending audio at 12% volume under speech."
                            },
                            rumble: {
                                title: "GTA 6 Gameplay Breakdown - Lucia Vice City Reveal (High-Action Scene)",
                                description: "Full commentary and breakdown of Grand Theft Auto VI high-octane viral moment.",
                                tags: "gta 6, grand theft auto 6, rockstar games, vice city, gameplay"
                            }
                        }
                    },
                    {
                        clip_id: '9e312eb2_2',
                        filename: 'gta6_clip_9e312eb2_2.mp4',
                        url: '/api/clips/gta6_clip_9e312eb2_2.mp4',
                        duration: 35,
                        score: 91,
                        reasons: ['🚗 High Speed Police Chase', '🌴 Vice City Nightclub Ambience', '🔊 Audio Dynamic Surge'],
                        seo: {
                            instagram: {
                                caption: "Vice City night graphics are unmatched 🌃✨ GTA 6 is going to break the internet!\\n\\n#GTA6 #Gaming #Rockstar #ViceCity"
                            },
                            youtube: {
                                title: "This GTA 6 Scene Is INSANE! 🔥 #shorts",
                                description: "Watch the police chase through downtown Vice City in GTA 6!",
                                tags: "gta 6, grand theft auto, gaming shorts, ps5 gameplay"
                            },
                            tiktok: {
                                caption: "The graphics in GTA 6 look like real life 😭 #gta6 #gaming #fyp",
                                sound_tip: "Original audio with bass boost"
                            },
                            rumble: {
                                title: "GTA 6 Vice City Night Chase Scene Breakdown",
                                description: "Detailed look at the police response and neon lighting in GTA 6.",
                                tags: "gta 6, rockstar, ps5, xbox"
                            }
                        }
                    }
                ];

                demoClips.forEach((clip, i) => {
                    const card = document.createElement('div');
                    card.className = 'clip-card';
                    card.id = 'demo-clip-card-' + i;
                    const reasonsHTML = clip.reasons.map(r => `<span class="reason-tag">${r}</span>`).join('');

                    card.innerHTML = `
                        <div class="clip-video-container">
                            <span class="clip-score-badge">🔥 ${clip.score}% Viral Score</span>
                            <video id="demo-video-${i}" controls playsinline preload="auto">
                                <source src="${clip.url}" type="video/mp4">
                            </video>
                        </div>
                        <div class="clip-meta-body">
                            <div>
                                <h4 style="font-size: 1.05rem; font-weight: 700; margin-bottom: 0.3rem;">Clip #${i+1} (${clip.duration}s)</h4>
                                <div class="clip-reasons">${reasonsHTML}</div>
                            </div>
                            <div class="seo-container">
                                <div class="seo-tabs" id="tabs-${i}">
                                    <button class="seo-tab-btn active" data-tab="ig">📸 Instagram</button>
                                    <button class="seo-tab-btn" data-tab="yt">🔴 YouTube</button>
                                    <button class="seo-tab-btn" data-tab="tt">🎵 TikTok</button>
                                    <button class="seo-tab-btn" data-tab="rb">🟢 Rumble</button>
                                </div>
                                <div class="seo-content-area" id="seo-box-${i}">${clip.seo.instagram.caption}</div>
                            </div>
                            <div class="clip-actions">
                                <button class="btn-copy" id="copy-btn-${i}">📋 Copy Caption</button>
                                <a href="${clip.url}" download="${clip.filename}" class="btn-download">⬇️ Download MP4</a>
                            </div>
                        </div>
                    `;
                    clipsGrid.appendChild(card);

                    // Add tab logic
                    const tabs = card.querySelectorAll('.seo-tab-btn');
                    const box = card.querySelector('#seo-box-' + i);
                    const copyBtn = card.querySelector('#copy-btn-' + i);

                    const texts = {
                        ig: clip.seo.instagram.caption,
                        yt: `${clip.seo.youtube.title}\\n\\n${clip.seo.youtube.description}\\n\\nTAGS:\\n${clip.seo.youtube.tags}`,
                        tt: `${clip.seo.tiktok.caption}\\n\\n💡 Sound Tip: ${clip.seo.tiktok.sound_tip}`,
                        rb: `${clip.seo.rumble.title}\\n\\n${clip.seo.rumble.description}\\n\\nTags: ${clip.seo.rumble.tags}`
                    };

                    tabs.forEach(btn => {
                        btn.addEventListener('click', () => {
                            tabs.forEach(b => b.classList.remove('active'));
                            btn.classList.add('active');
                            box.textContent = texts[btn.dataset.tab] || '';
                        });
                    });

                    copyBtn.addEventListener('click', () => {
                        copyBtn.textContent = '✅ Copied to Clipboard!';
                        copyBtn.style.background = 'rgba(16, 185, 129, 0.2)';
                        copyBtn.style.borderColor = '#10b981';
                        setTimeout(() => {
                            copyBtn.textContent = '📋 Copy Caption';
                            copyBtn.style.background = '';
                            copyBtn.style.borderColor = '';
                        }, 2500);
                    });
                });

                resultsSection.scrollIntoView({ behavior: 'smooth' });
            }
        """)

        # Wait for scroll
        time.sleep(1.2)

        # Hover over video container
        print("🎬 Starting video playback in browser...")
        page.hover("#demo-video-0")
        time.sleep(0.4)

        # Mark audio start time relative to script
        audio_start_walltime = time.time()
        # Play the video
        page.evaluate("""
            () => {
                const vid = document.getElementById('demo-video-0');
                if (vid) {
                    vid.muted = false;
                    vid.volume = 1.0;
                    vid.currentTime = 0;
                    vid.play();
                }
            }
        """)

        print(f"🔊 Video playback started at relative time. Recording playback...")
        time.sleep(2.0)

        # Switch SEO tabs on Clip #1
        print("🖱️ Switching SEO tabs...")
        page.hover("#tabs-0 [data-tab='yt']")
        time.sleep(0.3)
        page.click("#tabs-0 [data-tab='yt']")
        time.sleep(1.2)

        page.hover("#tabs-0 [data-tab='tt']")
        time.sleep(0.3)
        page.click("#tabs-0 [data-tab='tt']")
        time.sleep(1.2)

        page.hover("#tabs-0 [data-tab='ig']")
        time.sleep(0.3)
        page.click("#tabs-0 [data-tab='ig']")
        time.sleep(1.0)

        # Click Copy button
        print("📋 Clicking 'Copy Caption'...")
        page.hover("#copy-btn-0")
        time.sleep(0.3)
        page.click("#copy-btn-0")
        time.sleep(2.0)

        # Let the video play for another 4 seconds so viewer watches the animated subtitles
        print("👀 Watching video subtitles & action...")
        time.sleep(4.0)

        # Hover on second clip
        page.hover("#demo-clip-card-1")
        time.sleep(1.5)

        print("⏹️ Finalizing recording...")
        context.close()
        browser.close()

    # Find the created video
    webm_files = sorted(RECORDINGS_DIR.glob("*.webm"), key=os.path.getmtime, reverse=True)
    if webm_files:
        latest = webm_files[0]
        print(f"✅ Video recorded successfully: {latest} ({latest.stat().st_size} bytes)")
        return latest
    else:
        print("❌ No video file found!")
        return None

if __name__ == "__main__":
    record_demo()

