// Service worker: ponte entre a interface (popup / botão na página) e o native host.

const HOST_NAME = "com.ytbaixador.host";
const MAX_HISTORY = 30;

let port = null;
let downloads = {}; // id -> registro do download
let loaded = false;
const pending = new Map(); // reqId -> {resolve, timer}
let lastHostError = null;

// ------------------------------------------------------------------ estado

async function loadState() {
  if (loaded) return;
  const { downloads: saved = {} } = await chrome.storage.local.get("downloads");
  downloads = saved;
  // Downloads que estavam ativos quando o worker morreu perderam o acompanhamento.
  for (const d of Object.values(downloads)) {
    if (d.status === "queued" || d.status === "downloading" || d.status === "processing") {
      d.status = "unknown";
    }
  }
  loaded = true;
}

let saveTimer = null;
function saveState(immediate = false) {
  clearTimeout(saveTimer);
  const write = () => {
    const list = Object.values(downloads).sort((a, b) => b.created - a.created);
    for (const old of list.slice(MAX_HISTORY)) delete downloads[old.id];
    chrome.storage.local.set({ downloads });
  };
  if (immediate) write();
  else saveTimer = setTimeout(write, 300);
}

// ------------------------------------------------------------------- host

function getPort() {
  if (port) return port;
  port = chrome.runtime.connectNative(HOST_NAME);
  port.onMessage.addListener(onHostMessage);
  port.onDisconnect.addListener(() => {
    lastHostError = chrome.runtime.lastError?.message || "O host foi encerrado.";
    console.warn("Native host desconectado:", lastHostError);
    port = null;
    for (const [reqId, p] of pending) {
      clearTimeout(p.timer);
      p.resolve({ error: hostErrorText(lastHostError) });
      pending.delete(reqId);
    }
    for (const d of Object.values(downloads)) {
      if (d.status === "queued") {
        d.status = "error";
        d.error = hostErrorText(lastHostError);
      } else if (d.status === "downloading" || d.status === "processing") {
        d.status = "unknown";
      }
    }
    saveState(true);
  });
  return port;
}

function hostErrorText(msg) {
  if (/not found|não encontrado/i.test(msg || "")) {
    return "Native host não instalado. Rode host/install.sh e reinicie o navegador.";
  }
  return msg || "Falha ao falar com o native host.";
}

function request(msg, timeoutMs = 120000) {
  return new Promise((resolve) => {
    const reqId = crypto.randomUUID();
    const timer = setTimeout(() => {
      pending.delete(reqId);
      resolve({ error: "Tempo esgotado esperando o native host." });
    }, timeoutMs);
    pending.set(reqId, { resolve, timer });
    try {
      getPort().postMessage({ ...msg, reqId });
    } catch (e) {
      clearTimeout(timer);
      pending.delete(reqId);
      resolve({ error: hostErrorText(e.message) });
    }
  });
}

function onHostMessage(msg) {
  if (msg.type === "pong") {
    const p = pending.get("ping");
    if (p) {
      clearTimeout(p.timer);
      pending.delete("ping");
      p.resolve(msg);
    }
    return;
  }
  if (msg.reqId && pending.has(msg.reqId)) {
    const p = pending.get(msg.reqId);
    clearTimeout(p.timer);
    pending.delete(msg.reqId);
    p.resolve(msg);
    return;
  }
  const d = downloads[msg.id];
  if (!d) return;

  switch (msg.type) {
    case "started":
      d.status = "downloading";
      d.outdir = msg.outdir;
      break;
    case "progress":
      d.status = msg.status;
      d.percent = msg.percent;
      d.speed = msg.speed;
      d.eta = msg.eta;
      d.part = msg.part;
      break;
    case "done":
      d.status = "done";
      d.percent = 100;
      d.file = msg.file;
      d.outdir = msg.outdir;
      notify(d, "Download concluído", d.title);
      break;
    case "error":
      d.status = "error";
      d.error = msg.message;
      notify(d, "Falha no download", msg.message);
      break;
    case "cancelled":
      d.status = "cancelled";
      break;
  }
  d.updated = Date.now();
  saveState(msg.type !== "progress");
}

function ping() {
  return new Promise((resolve) => {
    const timer = setTimeout(() => {
      pending.delete("ping");
      resolve({ error: hostErrorText(lastHostError) });
    }, 15000);
    pending.set("ping", { resolve, timer });
    try {
      getPort().postMessage({ cmd: "ping" });
    } catch (e) {
      clearTimeout(timer);
      pending.delete("ping");
      resolve({ error: hostErrorText(e.message) });
    }
  });
}

function notify(d, title, message) {
  chrome.notifications.create(`ytb-${d.id}`, {
    type: "basic",
    iconUrl: "icons/icon128.png",
    title,
    message: message || "",
  });
}

chrome.notifications.onClicked.addListener((nid) => {
  const d = downloads[nid.replace(/^ytb-/, "")];
  if (d && (d.file || d.outdir)) getPort().postMessage({ cmd: "open", path: d.file || d.outdir });
});

// ------------------------------------------------------------- utilidades

function videoIdFromUrl(raw) {
  try {
    const u = new URL(raw);
    const host = u.hostname.replace(/^(www|m|music)\./, "");
    if (host === "youtu.be") return u.pathname.slice(1).split("/")[0] || null;
    if (host !== "youtube.com" && host !== "youtube-nocookie.com") return null;
    if (u.pathname === "/watch") return u.searchParams.get("v");
    const m = u.pathname.match(/^\/(shorts|live|embed|v)\/([\w-]{6,})/);
    return m ? m[2] : null;
  } catch {
    return null;
  }
}

async function startDownload({ url, title, preset }) {
  await loadState();
  const videoId = videoIdFromUrl(url);
  if (!videoId) return { error: "Isso não parece um vídeo do YouTube." };
  const { settings = {} } = await chrome.storage.local.get("settings");
  const id = crypto.randomUUID();
  downloads[id] = {
    id,
    videoId,
    url: `https://www.youtube.com/watch?v=${videoId}`,
    title: title || videoId,
    preset: preset || settings.preset || "best",
    status: "queued",
    percent: null,
    created: Date.now(),
    updated: Date.now(),
  };
  saveState(true);
  try {
    getPort().postMessage({
      cmd: "download",
      id,
      url: downloads[id].url,
      preset: downloads[id].preset,
      outdir: settings.outdir || "",
    });
  } catch (e) {
    downloads[id].status = "error";
    downloads[id].error = hostErrorText(e.message);
    saveState(true);
  }
  return { id };
}

// -------------------------------------------------------------- mensagens

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  (async () => {
    await loadState();
    switch (msg.type) {
      case "download":
        return startDownload(msg);
      case "cancel":
        getPort().postMessage({ cmd: "cancel", id: msg.id });
        return { ok: true };
      case "remove":
        delete downloads[msg.id];
        saveState(true);
        return { ok: true };
      case "clear":
        for (const d of Object.values(downloads)) {
          if (!["queued", "downloading", "processing"].includes(d.status)) delete downloads[d.id];
        }
        saveState(true);
        return { ok: true };
      case "open":
        getPort().postMessage({ cmd: "open", path: msg.path || "" });
        return { ok: true };
      case "info":
        return request({ cmd: "info", url: msg.url });
      case "ping":
        return ping();
      case "update":
        return request({ cmd: "update" }, 300000);
      case "videoId":
        return { videoId: videoIdFromUrl(msg.url) };
      default:
        return { error: "comando desconhecido" };
    }
  })()
    .then(sendResponse)
    .catch((e) => sendResponse({ error: hostErrorText(e.message) }));
  return true; // resposta assíncrona
});

loadState().then(() => saveState(true));
