// Live Monitoring Controls & Source Management
let isPaused = false;

document.addEventListener("DOMContentLoaded", () => {
    loadVideoSources();
    initStreamControls();
    initCalibrationSliders();
    initVideoUpload();
});

async function loadVideoSources() {
    try {
        const res = await fetch("/api/videos/sources");
        if (!res.ok) return;
        const data = await res.json();

        const select = document.getElementById("select-video-source");
        if (!select) return;

        select.innerHTML = "";

        // Add Samples
        if (data.samples && data.samples.length > 0) {
            const grpSamples = document.createElement("optgroup");
            grpSamples.label = "Sample Traffic Videos";
            data.samples.forEach(s => {
                const opt = document.createElement("option");
                opt.value = s.path;
                opt.innerText = `${s.name} (${s.size_mb} MB)`;
                grpSamples.appendChild(opt);
            });
            select.appendChild(grpSamples);
        }

        // Add Uploads
        if (data.uploads && data.uploads.length > 0) {
            const grpUploads = document.createElement("optgroup");
            grpUploads.label = "Uploaded Videos";
            data.uploads.forEach(u => {
                const opt = document.createElement("option");
                opt.value = u.path;
                opt.innerText = `${u.name} (${u.size_mb} MB)`;
                grpUploads.appendChild(opt);
            });
            select.appendChild(grpUploads);
        }

    } catch (err) {
        console.error("Error loading video sources:", err);
    }
}

function initStreamControls() {
    // Apply selected source
    const btnApply = document.getElementById("btn-apply-source");
    if (btnApply) {
        btnApply.addEventListener("click", async () => {
            const select = document.getElementById("select-video-source");
            const path = select.value;
            if (!path) return;

            try {
                const res = await fetch("/api/videos/select", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ source_type: "sample", source_path: path })
                });
                const resData = await res.json();
                if (res.ok) {
                    showToast(`Video loaded: ${path.split('\\\\').pop().split('/').pop()}`, "success");
                    document.getElementById("current-source-label").innerText = path.split('\\\\').pop().split('/').pop();
                    reloadStreamImage();
                } else {
                    showToast(resData.detail || "Error loading video", "danger");
                }
            } catch (e) {
                showToast("Connection error while loading video", "danger");
            }
        });
    }

    // Use Webcam
    const btnWebcam = document.getElementById("btn-use-webcam");
    if (btnWebcam) {
        btnWebcam.addEventListener("click", async () => {
            try {
                const res = await fetch("/api/videos/select", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ source_type: "webcam", webcam_index: 0 })
                });
                if (res.ok) {
                    showToast("Switched to Live Webcam #0", "success");
                    document.getElementById("current-source-label").innerText = "Webcam (Index 0)";
                    reloadStreamImage();
                } else {
                    showToast("Could not access webcam #0", "danger");
                }
            } catch (e) {
                showToast("Webcam initialization failed", "danger");
            }
        });
    }

    // Pause / Resume
    const btnPause = document.getElementById("btn-pause-stream");
    if (btnPause) {
        btnPause.addEventListener("click", async () => {
            const action = isPaused ? "resume" : "pause";
            try {
                const res = await fetch(`/api/monitoring/control?action=${action}`, { method: "POST" });
                const data = await res.json();
                isPaused = data.is_paused;
                btnPause.innerHTML = isPaused ? "&#9658; Resume" : "&#10074;&#10074; Pause";
                showToast(isPaused ? "Monitoring paused" : "Monitoring resumed", "info");
            } catch (e) {
                console.error(e);
            }
        });
    }

    // Reset Counters
    const btnReset = document.getElementById("btn-reset-counters");
    if (btnReset) {
        btnReset.addEventListener("click", async () => {
            try {
                await fetch("/api/monitoring/control?action=reset", { method: "POST" });
                showToast("Vehicle counters and trackers reset", "success");
                if (typeof fetchDashboardStats === "function") fetchDashboardStats();
            } catch (e) {
                console.error(e);
            }
        });
    }
}

function initCalibrationSliders() {
    const sliderLine = document.getElementById("slider-stop-line");
    const labelLine = document.getElementById("label-stop-line-val");
    if (sliderLine && labelLine) {
        sliderLine.addEventListener("input", () => {
            labelLine.innerText = `${sliderLine.value}%`;
        });
    }

    const sliderConf = document.getElementById("slider-confidence");
    const labelConf = document.getElementById("label-conf-val");
    if (sliderConf && labelConf) {
        sliderConf.addEventListener("input", () => {
            labelConf.innerText = (sliderConf.value / 100).toFixed(2);
        });
    }

    // Apply Settings
    const btnSave = document.getElementById("btn-save-settings");
    if (btnSave) {
        btnSave.addEventListener("click", async () => {
            const stopPct = parseFloat(sliderLine.value) / 100.0;
            const conf = parseFloat(sliderConf.value) / 100.0;
            const dir = document.getElementById("select-lane-direction").value;

            try {
                const res = await fetch("/api/monitoring/settings", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        stop_line_y: stopPct,
                        confidence_threshold: conf,
                        allowed_direction: dir
                    })
                });
                if (res.ok) {
                    showToast("Calibration settings applied", "success");
                }
            } catch (e) {
                showToast("Error updating calibration", "danger");
            }
        });
    }

    // Signal Mode Dropdown
    const selMode = document.getElementById("select-signal-mode");
    if (selMode) {
        selMode.addEventListener("change", () => {
            setSignalMode(selMode.value);
        });
    }
}

async function setSignalMode(mode) {
    try {
        const res = await fetch("/api/monitoring/settings", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ traffic_light_mode: mode })
        });
        if (res.ok) {
            const selMode = document.getElementById("select-signal-mode");
            if (selMode) selMode.value = mode;
            showToast(`Traffic Signal set to ${mode.replace('_', ' ').toUpperCase()}`, "info");
        }
    } catch (e) {
        console.error(e);
    }
}

function initVideoUpload() {
    const btnUpload = document.getElementById("btn-upload-video");
    const fileInput = document.getElementById("input-video-file");

    if (btnUpload && fileInput) {
        btnUpload.addEventListener("click", async () => {
            if (!fileInput.files || fileInput.files.length === 0) {
                showToast("Please choose a video file to upload", "danger");
                return;
            }

            const file = fileInput.files[0];
            const formData = new FormData();
            formData.append("file", file);
            formData.append("auto_play", "true");

            showToast("Uploading and loading video...", "info");

            try {
                const res = await fetch("/api/videos/upload", {
                    method: "POST",
                    body: formData
                });
                const data = await res.json();
                if (res.ok) {
                    showToast(`Video uploaded: ${data.filename}`, "success");
                    document.getElementById("current-source-label").innerText = data.filename;
                    loadVideoSources();
                    reloadStreamImage();
                } else {
                    showToast(data.detail || "Upload failed", "danger");
                }
            } catch (e) {
                showToast("Video upload failed", "danger");
            }
        });
    }
}

function reloadStreamImage() {
    const img = document.getElementById("live-stream-img");
    if (img) {
        img.src = `/api/monitoring/stream?t=${new Date().getTime()}`;
    }
}
