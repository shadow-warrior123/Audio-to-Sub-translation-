const state = {
  selectedFile: null,
  jobId: null,
  pollTimer: null,
};

const els = {
  healthBadge: document.querySelector("#healthBadge"),
  healthDetails: document.querySelector("#healthDetails"),
  dropZone: document.querySelector("#dropZone"),
  videoInput: document.querySelector("#videoInput"),
  fileTitle: document.querySelector("#fileTitle"),
  fileMeta: document.querySelector("#fileMeta"),
  whisperModel: document.querySelector("#whisperModel"),
  translationModel: document.querySelector("#translationModel"),
  processButton: document.querySelector("#processButton"),
  resetButton: document.querySelector("#resetButton"),
  statusPanel: document.querySelector("#statusPanel"),
  errorPanel: document.querySelector("#errorPanel"),
  statusLabel: document.querySelector("#statusLabel"),
  progressLabel: document.querySelector("#progressLabel"),
  progressFill: document.querySelector("#progressFill"),
  stepText: document.querySelector("#stepText"),
  logBox: document.querySelector("#logBox"),
  resultPanel: document.querySelector("#resultPanel"),
  videoPreview: document.querySelector("#videoPreview"),
  videoDownload: document.querySelector("#videoDownload"),
  subtitleDownload: document.querySelector("#subtitleDownload"),
};

init();

function init() {
  loadHealth();
  bindUpload();
  els.processButton.addEventListener("click", startJob);
  els.resetButton.addEventListener("click", reset);
}

async function loadHealth() {
  try {
    const health = await getJson("/health");
    els.healthBadge.textContent = health.ffmpeg ? "Ready" : "FFmpeg unavailable";
    els.healthBadge.classList.toggle("ready", Boolean(health.ffmpeg));
    els.healthDetails.innerHTML = `
      <div><dt>FFmpeg</dt><dd>${health.ffmpeg ? "Available" : "Missing"}</dd></div>
      <div><dt>Whisper</dt><dd>${escapeHtml(health.whisper_model_size)}</dd></div>
      <div><dt>Translation</dt><dd>${escapeHtml(health.translation_model)}</dd></div>
      <div><dt>Device</dt><dd>ASR ${escapeHtml(health.whisper_device)} / Translation ${escapeHtml(health.translation_device)}</dd></div>
    `;
    populateModelSelects(health);
  } catch (error) {
    els.healthBadge.textContent = "Backend offline";
    showError(error.message);
  }
}

function bindUpload() {
  els.videoInput.addEventListener("change", () => {
    const file = els.videoInput.files?.[0];
    if (file) selectFile(file);
  });

  ["dragenter", "dragover"].forEach((eventName) => {
    els.dropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      els.dropZone.classList.add("dragging");
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    els.dropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      els.dropZone.classList.remove("dragging");
    });
  });

  els.dropZone.addEventListener("drop", (event) => {
    const file = event.dataTransfer.files?.[0];
    if (file) selectFile(file);
  });
}

function selectFile(file) {
  hideError();
  const lowerName = file.name.toLowerCase();
  if (!lowerName.endsWith(".mp4") && !lowerName.endsWith(".mkv")) {
    showError("Please choose an MP4 or MKV video.");
    return;
  }
  state.selectedFile = file;
  els.fileTitle.textContent = file.name;
  els.fileMeta.textContent = `${formatBytes(file.size)} selected`;
  els.processButton.disabled = false;
  els.resultPanel.classList.add("hidden");
}

async function startJob() {
  if (!state.selectedFile) return;
  hideError();
  els.processButton.disabled = true;
  els.statusPanel.classList.remove("hidden");
  els.resultPanel.classList.add("hidden");
  updateStatus({ status: "uploading", progress: 0, step: "uploading", logs: ["Uploading video"] });

  const body = new FormData();
  body.append("file", state.selectedFile);
  body.append("whisper_model_size", els.whisperModel.value);
  body.append("translation_model", els.translationModel.value);

  try {
    const response = await fetch("/jobs", { method: "POST", body });
    if (!response.ok) {
      throw new Error(await response.text());
    }
    const job = await response.json();
    state.jobId = job.id;
    updateStatus(job);
    startPolling();
  } catch (error) {
    els.processButton.disabled = false;
    showError(error.message);
  }
}

function startPolling() {
  stopPolling();
  state.pollTimer = window.setInterval(fetchJob, 2000);
  fetchJob();
}

function stopPolling() {
  if (state.pollTimer) {
    window.clearInterval(state.pollTimer);
    state.pollTimer = null;
  }
}

async function fetchJob() {
  if (!state.jobId) return;
  try {
    const job = await getJson(`/jobs/${state.jobId}`);
    updateStatus(job);
    if (job.status === "completed") {
      stopPolling();
      showResult(job.id);
    } else if (job.status === "failed") {
      stopPolling();
      els.processButton.disabled = false;
      showError(job.error || "Processing failed.");
    }
  } catch (error) {
    stopPolling();
    els.processButton.disabled = false;
    showError(error.message);
  }
}

function updateStatus(job) {
  const progress = Number(job.progress || 0);
  els.statusLabel.textContent = titleCase(job.status || "queued");
  els.progressLabel.textContent = `${progress}%`;
  els.progressFill.style.width = `${Math.min(100, Math.max(0, progress))}%`;
  els.stepText.textContent = titleCase(String(job.step || "queued").replaceAll("_", " "));
  els.logBox.textContent = Array.isArray(job.logs) ? job.logs.join("\n") : "";
}

function populateModelSelects(health) {
  fillSelect(els.whisperModel, health.model_options?.whisper || [], health.whisper_model_size);
  fillSelect(els.translationModel, health.model_options?.translation || [], health.translation_model);
}

function fillSelect(select, options, selectedValue) {
  select.innerHTML = "";
  for (const optionValue of options) {
    const option = document.createElement("option");
    option.value = optionValue;
    option.textContent = optionValue;
    option.selected = optionValue === selectedValue;
    select.appendChild(option);
  }
}

function showResult(jobId) {
  const videoUrl = `/jobs/${jobId}/video`;
  const subtitleUrl = `/jobs/${jobId}/subtitle`;
  els.videoPreview.src = videoUrl;
  els.videoDownload.href = videoUrl;
  els.subtitleDownload.href = subtitleUrl;
  els.resultPanel.classList.remove("hidden");
}

function reset() {
  stopPolling();
  state.selectedFile = null;
  state.jobId = null;
  els.videoInput.value = "";
  els.fileTitle.textContent = "Choose or drop a video";
  els.fileMeta.textContent = "MP4 or MKV, processed locally through the backend.";
  els.processButton.disabled = true;
  els.statusPanel.classList.add("hidden");
  els.resultPanel.classList.add("hidden");
  els.videoPreview.removeAttribute("src");
  els.videoPreview.load();
  hideError();
}

async function getJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

function showError(message) {
  els.errorPanel.textContent = message;
  els.errorPanel.classList.remove("hidden");
}

function hideError() {
  els.errorPanel.classList.add("hidden");
  els.errorPanel.textContent = "";
}

function formatBytes(bytes) {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / 1024 ** index).toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

function titleCase(value) {
  return value.replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
