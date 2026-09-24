// Polls /api/logs for real log entries written by logger.py, applies the
// level filter + search box, and auto-scrolls while "LIVE" is enabled.

const stream = document.getElementById("logStream");
const searchBox = document.getElementById("searchBox");
const levelFilter = document.getElementById("levelFilter");
const liveToggle = document.getElementById("liveToggle");
const refreshMs = Math.max(2, parseInt(document.currentScript.dataset.refresh || "5", 10)) * 1000;

let live = true;

const LEVEL_CLASS = {
  ERROR: "text-primary", CRITICAL: "text-primary",
  WARNING: "text-[#ffc107]", DEBUG: "text-outline", INFO: "text-secondary",
};

function renderEntries(entries) {
  stream.innerHTML = "";
  if (!entries.length) {
    stream.innerHTML = `<div class="text-on-surface-variant">No matching log entries.</div>`;
    return;
  }
  for (const e of entries) {
    const row = document.createElement("div");
    row.className = "log-row flex items-start gap-3 py-0.5 hover:bg-surface-container-low/60";
    row.innerHTML = `
      <span class="text-outline shrink-0">${e.time}</span>
      <span class="shrink-0 ${LEVEL_CLASS[e.level] || "text-secondary"}">[${e.level}]</span>
      <span class="text-on-surface-variant shrink-0">${e.module}:</span>
      <span class="text-on-surface">${e.message}</span>`;
    stream.appendChild(row);
  }
  if (live) stream.scrollTop = stream.scrollHeight;
}

async function refresh() {
  const params = new URLSearchParams({
    level: levelFilter.value,
    q: searchBox.value || "",
    limit: "300",
  });
  const res = await fetch(`/api/logs?${params}`);
  if (res.ok) renderEntries(await res.json());
}

liveToggle.addEventListener("click", () => {
  live = !live;
  liveToggle.classList.toggle("text-tertiary", live);
  liveToggle.classList.toggle("text-outline", !live);
  liveToggle.innerHTML = live
    ? `<span class="w-1.5 h-1.5 rounded-full bg-tertiary animate-pulse"></span> LIVE`
    : `<span class="w-1.5 h-1.5 rounded-full bg-outline"></span> PAUSED`;
});

searchBox.addEventListener("input", refresh);
levelFilter.addEventListener("change", refresh);

setInterval(() => { if (live) refresh(); }, refreshMs);
