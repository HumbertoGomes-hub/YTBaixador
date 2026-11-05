const $ = (id) => document.getElementById(id);
const ACTIVE = ["queued", "downloading", "processing"];
const PRESET_LABELS = {
  best: "melhor qualidade",
  1080: "1080p",
  720: "720p",
  480: "480p",
  mp3: "MP3",
  m4a: "M4A",
};

let tab = null;
let settings = {};
let hostDefaultOutdir = "";

const send = (msg) => chrome.runtime.sendMessage(msg);

// ------------------------------------------------------------- formatação

function fmtBytes(n) {
  if (!n) return "";
  const units = ["B", "KB", "MB", "GB"];
  let i = 0;
  while (n >= 1024 && i < units.length - 1) { n /= 1024; i++; }
  return `${n.toFixed(i ? 1 : 0)} ${units[i]}`;
}

function fmtTime(s) {
  if (s == null) return "";
  s = Math.round(s);
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
  return (h ? `${h}:${String(m).padStart(2, "0")}` : `${m}`) + `:${String(sec).padStart(2, "0")}`;
}

function statusText(d) {
  switch (d.status) {
    case "queued": return "Na fila…";
    case "downloading": {
      const parts = [];
      if (d.percent != null) parts.push(`${d.percent.toFixed(1)}%`);
      if (d.speed) parts.push(`${fmtBytes(d.speed)}/s`);
      if (d.eta != null) parts.push(`faltam ${fmtTime(d.eta)}`);
      if (d.part > 1) parts.push(`parte ${d.part}`);
      return parts.join(" · ") || "Baixando…";
    }
    case "processing": return "Processando (ffmpeg)…";
    case "done": return "Concluído";
    case "cancelled": return "Cancelado";
    case "unknown": return "Acompanhamento perdido (o download pode ter terminado)";
    case "error": return d.error || "Erro";
    default: return d.status;
  }
}

// ------------------------------------------------------------------ lista

function renderList(downloads) {
  const list = $("list");
  const items = Object.values(downloads || {}).sort((a, b) => b.created - a.created);
  $("empty").hidden = items.length > 0;
  list.replaceChildren(
    ...items.map((d) => {
      const li = document.createElement("li");

      const top = document.createElement("div");
      top.className = "item-top";
      const title = document.createElement("div");
      title.className = "item-title";
      title.textContent = d.title;
      title.title = `${d.title} (${PRESET_LABELS[d.preset] || d.preset})`;
      const actions = document.createElement("div");
      actions.className = "item-actions";

      const addAction = (label, fn) => {
        const b = document.createElement("button");
        b.className = "link";
        b.textContent = label;
        b.addEventListener("click", fn);
        actions.appendChild(b);
      };
      if (ACTIVE.includes(d.status)) {
        addAction("Cancelar", () => send({ type: "cancel", id: d.id }));
      } else {
        if (d.status === "done") addAction("Abrir pasta", () => send({ type: "open", path: d.file || d.outdir }));
        if (d.status === "error" || d.status === "cancelled") {
          addAction("Tentar de novo", () => send({ type: "download", url: d.url, title: d.title, preset: d.preset }));
        }
        addAction("✕", () => send({ type: "remove", id: d.id }));
      }
      top.append(title, actions);
      li.appendChild(top);

      if (ACTIVE.includes(d.status)) {
        const bar = document.createElement("div");
        bar.className = "bar";
        const fill = document.createElement("div");
        if (d.percent == null || d.status === "processing") bar.classList.add("indeterminate");
        else fill.style.width = `${d.percent}%`;
        bar.appendChild(fill);
        li.appendChild(bar);
      }

      const status = document.createElement("div");
      status.className = `status ${d.status}`;
      status.textContent = statusText(d);
      li.appendChild(status);
      return li;
    }),
  );
}

// ------------------------------------------------------------ vídeo atual

async function loadCurrentVideo() {
  [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const { videoId } = await send({ type: "videoId", url: tab?.url || "" });
  if (!videoId) return;

  $("notVideo").hidden = true;
  $("videoBox").hidden = false;
  $("title").textContent = (tab.title || "").replace(/^\(\d+\)\s*/, "").replace(/ - YouTube$/, "");
  $("thumb").src = `https://i.ytimg.com/vi/${videoId}/mqdefault.jpg`;
  $("meta").textContent = "Carregando detalhes…";

  const info = await send({ type: "info", url: tab.url });
  if (info?.error) {
    $("meta").textContent = "";
    return;
  }
  if (info.title) $("title").textContent = info.title;
  const bits = [info.uploader, fmtTime(info.duration)];
  if (info.heights?.length) bits.push(`até ${info.heights[0]}p`);
  $("meta").textContent = bits.filter(Boolean).join(" · ");

  // Desabilita resoluções que o vídeo não tem.
  if (info.heights?.length) {
    const max = info.heights[0];
    for (const opt of $("preset").options) {
      const h = Number(opt.value);
      if (h && h > max) opt.disabled = true;
    }
    if ($("preset").selectedOptions[0]?.disabled) $("preset").value = "best";
  }
}

// ------------------------------------------------------------------- host

async function checkHost() {
  const res = await send({ type: "ping" });
  const banner = $("hostStatus");
  if (res?.error) {
    banner.hidden = false;
    banner.innerHTML = "";
    banner.append(res.error, document.createElement("br"));
    const code = document.createElement("code");
    code.textContent = "./host/install.sh";
    banner.append("No terminal, na pasta do projeto: ", code);
    $("download").disabled = true;
    return;
  }
  hostDefaultOutdir = res.defaultOutdir || "";
  $("outdir").placeholder = `Padrão: ${hostDefaultOutdir}`;
  const problems = [];
  if (!res.ytdlp) problems.push("yt-dlp não encontrado — rode host/install.sh.");
  if (!res.ffmpeg) problems.push("ffmpeg não encontrado — instale com: sudo apt install ffmpeg");
  if (!res.jsRuntime) problems.push("Nenhum runtime JavaScript (deno/node) — o YouTube pode falhar.");
  if (problems.length) {
    banner.hidden = false;
    banner.textContent = problems.join(" ");
  }
  $("hostInfo").textContent =
    `yt-dlp ${res.ytdlpVersion || "?"} · ffmpeg ${res.ffmpeg ? "ok" : "ausente"} · JS ${res.jsRuntime ? res.jsRuntime.split("/").pop() : "ausente"}`;
}

// ------------------------------------------------------------------ init

async function init() {
  ({ settings = {} } = await chrome.storage.local.get("settings"));
  $("outdir").value = settings.outdir || "";
  if (settings.preset) $("preset").value = settings.preset;

  const { downloads } = await chrome.storage.local.get("downloads");
  renderList(downloads);
  chrome.storage.onChanged.addListener((changes, area) => {
    if (area === "local" && changes.downloads) renderList(changes.downloads.newValue);
  });

  $("settingsToggle").addEventListener("click", () => ($("settings").hidden = !$("settings").hidden));

  $("outdir").addEventListener("change", () => {
    settings.outdir = $("outdir").value.trim();
    chrome.storage.local.set({ settings });
  });
  $("preset").addEventListener("change", () => {
    settings.preset = $("preset").value;
    chrome.storage.local.set({ settings });
  });

  $("download").addEventListener("click", async () => {
    $("download").disabled = true;
    const res = await send({
      type: "download",
      url: tab.url,
      title: $("title").textContent,
      preset: $("preset").value,
    });
    if (res?.error) alert(res.error);
    setTimeout(() => ($("download").disabled = false), 800);
  });

  $("clear").addEventListener("click", () => send({ type: "clear" }));
  $("openFolder").addEventListener("click", () => send({ type: "open", path: settings.outdir || "" }));
  $("updateYtdlp").addEventListener("click", async () => {
    const btn = $("updateYtdlp");
    btn.disabled = true;
    btn.textContent = "Atualizando…";
    const res = await send({ type: "update" });
    btn.disabled = false;
    btn.textContent = "Atualizar yt-dlp";
    $("hostInfo").textContent = res.error || `yt-dlp ${res.version} — ${res.ok ? "atualizado" : "falhou"}`;
  });

  await checkHost();
  loadCurrentVideo();
}

init();
