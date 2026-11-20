// Frontend reactive controller for GTA 6 Viral Clipper

document.addEventListener("DOMContentLoaded", () => {
  // Elements
  const urlInput = document.getElementById("video-url");
  const pasteBtn = document.getElementById("paste-btn");
  const dropZone = document.getElementById("drop-zone");
  const fileInput = document.getElementById("file-input");
  const dropContent = document.getElementById("drop-content");
  const presetPills = document.querySelectorAll(".preset-pill");
  const layoutCards = document.querySelectorAll("#layout-group .radio-card");
  const subtitleCards = document.querySelectorAll("#subtitle-group .radio-card");
  const clipsSlider = document.getElementById("clips-slider");
  const clipsVal = document.getElementById("clips-val");
  const durSlider = document.getElementById("dur-slider");
  const durVal = document.getElementById("dur-val");
  const antiCopyrightToggle = document.getElementById("anti-copyright-toggle");
  const generateBtn = document.getElementById("generate-btn");

  const progressCard = document.getElementById("progress-card");
  const progressFill = document.getElementById("progress-fill");
  const progressPct = document.getElementById("progress-pct");
  const progressTitle = document.getElementById("progress-status-title");
  const progressDetail = document.getElementById("progress-status-detail");
  const terminalBody = document.getElementById("terminal-body");

  const resultsSection = document.getElementById("results-section");
  const clipsGrid = document.getElementById("clips-grid");
  const hwBadge = document.getElementById("hw-badge");

  let uploadedFilePath = null;

  // 1. Check Health & GPU encoder
  fetch("/api/health")
    .then(r => r.json())
    .then(data => {
      if (data.encoder === "h264_videotoolbox") {
        hwBadge.textContent = "⚡ Apple Silicon VideoToolbox Active (Ultra Fast)";
      } else {
        hwBadge.textContent = `⚡ FFmpeg Encoder: ${data.encoder}`;
      }
    })
    .catch(() => {});

  // 2. Paste Clipboard
  pasteBtn.addEventListener("click", async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text && (text.includes("http") || text.includes("youtube") || text.includes("youtu.be"))) {
        urlInput.value = text.trim();
        uploadedFilePath = null;
      }
    } catch (e) {
      alert("Please allow clipboard permission or paste manually.");
    }
  });

  // 3. File Drag & Drop
  dropZone.addEventListener("click", () => fileInput.click());
  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("dragover");
  });
  dropZone.addEventListener("dragleave", () => dropZone.classList.remove("dragover"));
  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("dragover");
    if (e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener("change", () => {
    if (fileInput.files.length > 0) {
      handleFileUpload(fileInput.files[0]);
    }
  });

  async function handleFileUpload(file) {
    dropContent.innerHTML = `<p>⏳ Uploading <strong>${file.name}</strong>...</p>`;
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("/api/upload", {
        method: "POST",
        body: formData
      });
      const data = await res.json();
      uploadedFilePath = data.file_path;
      urlInput.value = `[Local File] ${file.name}`;
      dropContent.innerHTML = `<p>✅ Loaded: <strong>${file.name}</strong> (${(file.size / (1024*1024)).toFixed(1)} MB)</p>`;
    } catch (err) {
      dropContent.innerHTML = `<p style="color: #ef4444;">Upload failed: ${err.message}</p>`;
    }
  }

  // 4. Presets Selection
  const PRESET_MAP = {
    "gta6_viral": { layout: "split", dur: 40, sub: "hormozi", anti: true },
    "story_cutscene": { layout: "blur", dur: 50, sub: "vice_city", anti: true },
    "action_montage": { layout: "crop", dur: 35, sub: "hormozi", anti: true },
  };

  presetPills.forEach(pill => {
    pill.addEventListener("click", () => {
      presetPills.forEach(p => p.classList.remove("active"));
      pill.classList.add("active");

      const cfg = PRESET_MAP[pill.dataset.preset];
      if (cfg) {
        selectRadio("#layout-group", cfg.layout);
        selectRadio("#subtitle-group", cfg.sub);
        durSlider.value = cfg.dur;
        durVal.textContent = `${cfg.dur} Seconds`;
        antiCopyrightToggle.checked = cfg.anti;
      }
    });
  });

  function selectRadio(groupSelector, val) {
    const cards = document.querySelectorAll(`${groupSelector} .radio-card`);
    cards.forEach(c => {
      const input = c.querySelector("input");
      if (input.value === val) {
        input.checked = true;
        c.classList.add("active");
      } else {
        c.classList.remove("active");
      }
    });
  }

  // Radio cards click handlers
  function bindRadioGroup(groupSelector) {
    const cards = document.querySelectorAll(`${groupSelector} .radio-card`);
    cards.forEach(c => {
      c.addEventListener("click", () => {
        cards.forEach(other => other.classList.remove("active"));
        c.classList.add("active");
      });
    });
  }
  bindRadioGroup("#layout-group");
  bindRadioGroup("#subtitle-group");
  bindRadioGroup("#section-group");

  // Sliders
  clipsSlider.addEventListener("input", (e) => {
    clipsVal.textContent = `${e.target.value} Clip${e.target.value > 1 ? 's' : ''}`;
  });
  durSlider.addEventListener("input", (e) => {
    durVal.textContent = `${e.target.value} Seconds`;
  });

  // Log to terminal
  function appendLog(msg, isSuccess = false) {
    const line = document.createElement("div");
    line.className = `log-line ${isSuccess ? 'success' : 'info'}`;
    line.textContent = `[${new Date().toLocaleTimeString()}] ${msg}`;
    terminalBody.appendChild(line);
    terminalBody.scrollTop = terminalBody.scrollHeight;
  }

  // 5. Generate Clips Trigger
  generateBtn.addEventListener("click", async () => {
    const url = uploadedFilePath || urlInput.value.trim();
    if (!url) {
      alert("Please provide a YouTube video URL or drop a local video file!");
      return;
    }

    const layout = document.querySelector("#layout-group input:checked").value;
    const subStyle = document.querySelector("#subtitle-group input:checked").value;
    const sectionInput = document.querySelector("#section-group input:checked");
    const videoSection = sectionInput ? sectionInput.value : "full";
    const targetClips = parseInt(clipsSlider.value);
    const clipDur = parseFloat(durSlider.value);
    const antiCopy = antiCopyrightToggle.checked;

    // Reset UI
    progressCard.style.display = "block";
    resultsSection.style.display = "none";
    clipsGrid.innerHTML = "";
    terminalBody.innerHTML = "";
    generateBtn.disabled = true;
    generateBtn.style.opacity = "0.5";

    appendLog(`Job initialized for: ${url.startsWith("http") ? url : "Local video"}`);
    appendLog(`Settings: Layout=${layout}, Subtitles=${subStyle}, Section=${videoSection}, AntiCopyright=${antiCopy}`);

    try {
      const response = await fetch("/api/clip", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: url,
          target_clips: targetClips,
          clip_duration: clipDur,
          layout: layout,
          enable_anti_copyright: antiCopy,
          subtitle_style: subStyle,
          video_section: videoSection
        })
      });

      const { job_id } = await response.json();
      appendLog(`Server assigned Job ID: ${job_id}`);

      // Listen via SSE
      const evtSource = new EventSource(`/api/jobs/${job_id}/stream`);

      evtSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        const pct = data.progress;
        const msg = data.message;

        progressFill.style.width = `${pct}%`;
        progressPct.textContent = `${pct}%`;
        progressTitle.textContent = pct === 100 ? "Processing Complete!" : "Creating Viral Clips...";
        progressDetail.textContent = msg;

        appendLog(`[${pct}%] ${msg}`);

        if (data.status === "completed") {
          evtSource.close();
          appendLog("All clips ready for multi-platform publishing! 🎉", true);
          generateBtn.disabled = false;
          generateBtn.style.opacity = "1";
          renderResults(data.result.clips);
        } else if (data.status === "failed") {
          evtSource.close();
          appendLog(`ERROR: ${data.error}`, false);
          alert(`Error processing video: ${data.error}`);
          generateBtn.disabled = false;
          generateBtn.style.opacity = "1";
        }
      };

      evtSource.onerror = () => {
        evtSource.close();
        generateBtn.disabled = false;
        generateBtn.style.opacity = "1";
      };

    } catch (e) {
      alert(`Request failed: ${e.message}`);
      generateBtn.disabled = false;
      generateBtn.style.opacity = "1";
    }
  });

  // 6. Render Results & SEO Tabs
  function renderResults(clips) {
    resultsSection.style.display = "block";
    resultsSection.scrollIntoView({ behavior: "smooth" });

    clips.forEach((clip, i) => {
      const card = document.createElement("div");
      card.className = "clip-card";

      const reasonsHTML = clip.reasons.map(r => `<span class="reason-tag">${r}</span>`).join("");

      card.innerHTML = `
        <div class="clip-video-container">
          <span class="clip-score-badge">🔥 ${clip.score}% Viral Score</span>
          <video controls playsinline preload="metadata">
            <source src="${clip.url}" type="video/mp4">
            Your browser does not support HTML5 video.
          </video>
        </div>
        <div class="clip-meta-body">
          <div>
            <h4 style="font-size: 1.05rem; font-weight: 700; margin-bottom: 0.3rem;">Clip #${i+1} (${clip.duration}s)</h4>
            <div class="clip-reasons">${reasonsHTML}</div>
          </div>

          <!-- SEO Platform Tabs -->
          <div class="seo-container">
            <div class="seo-tabs" id="tabs-${i}">
              <button class="seo-tab-btn active" data-tab="ig">📸 Instagram</button>
              <button class="seo-tab-btn" data-tab="yt">🔴 YouTube</button>
              <button class="seo-tab-btn" data-tab="tt">🎵 TikTok</button>
              <button class="seo-tab-btn" data-tab="rb">🟢 Rumble</button>
            </div>
            <div class="seo-content-area" id="seo-box-${i}">${clip.seo.instagram.caption}</div>
            <div class="sound-tip-banner" id="sound-tip-${i}" style="display: none;">
              🎧 <strong>Sound Tip:</strong> <span>${clip.seo.tiktok.sound_tip || "Use trending viral audio"}</span>
            </div>
          </div>

          <div class="clip-actions">
            <button class="btn-copy" id="copy-btn-${i}">📋 Copy Caption</button>
            <a href="${clip.url}" download="${clip.filename}" class="btn-download">⬇️ Download MP4</a>
          </div>
        </div>
      `;

      clipsGrid.appendChild(card);

      // Tab click events
      const tabBtns = card.querySelectorAll(".seo-tab-btn");
      const contentBox = card.querySelector(`#seo-box-${i}`);
      const soundTipBox = card.querySelector(`#sound-tip-${i}`);
      const copyBtn = card.querySelector(`#copy-btn-${i}`);

      let currentPlatform = "ig";

      const getPlatformText = (plat) => {
        if (plat === "ig") return clip.seo.instagram.caption;
        if (plat === "yt") return `${clip.seo.youtube.title}\n\n${clip.seo.youtube.description}\n\nTAGS:\n${clip.seo.youtube.tags}`;
        if (plat === "tt") return clip.seo.tiktok.caption; // Clean caption only - no soundtip contamination!
        if (plat === "rb") return `${clip.seo.rumble.title}\n\n${clip.seo.rumble.description}\n\nTags: ${clip.seo.rumble.tags}`;
        return "";
      };

      tabBtns.forEach(btn => {
        btn.addEventListener("click", () => {
          tabBtns.forEach(b => b.classList.remove("active"));
          btn.classList.add("active");
          currentPlatform = btn.dataset.tab;
          contentBox.textContent = getPlatformText(currentPlatform);

          // Show sound tip banner advisory only on TikTok tab
          if (currentPlatform === "tt" && clip.seo.tiktok.sound_tip) {
            soundTipBox.style.display = "flex";
          } else {
            soundTipBox.style.display = "none";
          }
        });
      });

      copyBtn.addEventListener("click", () => {
        navigator.clipboard.writeText(contentBox.textContent).then(() => {
          const original = copyBtn.textContent;
          copyBtn.textContent = "✅ Copied to Clipboard!";
          copyBtn.style.background = "rgba(16, 185, 129, 0.2)";
          copyBtn.style.borderColor = "#10b981";
          setTimeout(() => {
            copyBtn.textContent = original;
            copyBtn.style.background = "";
            copyBtn.style.borderColor = "";
          }, 2000);
        });
      });
    });
  }
});

