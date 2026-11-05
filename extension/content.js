// Injeta um botão "Baixar" nas páginas de vídeo do YouTube.

(() => {
  const PRESETS = [
    ["best", "Vídeo · melhor qualidade"],
    ["1080", "Vídeo · 1080p (MP4)"],
    ["720", "Vídeo · 720p (MP4)"],
    ["480", "Vídeo · 480p (MP4)"],
    ["mp3", "Áudio · MP3"],
    ["m4a", "Áudio · M4A"],
  ];
  const ACTIVE = ["queued", "downloading", "processing"];
  const ANCHORS = [
    "ytd-watch-metadata #top-level-buttons-computed",
    "ytd-watch-metadata #actions-inner #menu",
    "ytd-watch-metadata #actions",
  ];

  let wrap = null;
  let button = null;
  let menu = null;
  let downloads = {};

  function currentVideoId() {
    const u = new URL(location.href);
    if (u.pathname === "/watch") return u.searchParams.get("v");
    const m = u.pathname.match(/^\/(shorts|live)\/([\w-]{6,})/);
    return m ? m[2] : null;
  }

  function videoTitle() {
    const el = document.querySelector("ytd-watch-metadata h1 yt-formatted-string, ytd-watch-metadata h1");
    return (el?.textContent || document.title.replace(/ - YouTube$/, "")).trim();
  }

  function build() {
    wrap = document.createElement("div");
    wrap.className = "ytb-wrap";

    button = document.createElement("button");
    button.className = "ytb-btn";
    button.type = "button";
    button.title = "Baixar com YT Baixador";
    button.addEventListener("click", (e) => {
      e.stopPropagation();
      menu.hidden = !menu.hidden;
    });

    menu = document.createElement("div");
    menu.className = "ytb-menu";
    menu.hidden = true;
    for (const [preset, label] of PRESETS) {
      const item = document.createElement("button");
      item.type = "button";
      item.className = "ytb-item";
      item.textContent = label;
      item.addEventListener("click", async (e) => {
        e.stopPropagation();
        menu.hidden = true;
        const res = await chrome.runtime.sendMessage({
          type: "download",
          url: location.href,
          title: videoTitle(),
          preset,
        });
        if (res?.error) alert("YT Baixador: " + res.error);
      });
      menu.appendChild(item);
    }

    wrap.append(button, menu);
    document.addEventListener("click", () => menu && (menu.hidden = true));
    render();
  }

  function render() {
    if (!button) return;
    const vid = currentVideoId();
    const active = Object.values(downloads)
      .filter((d) => d.videoId === vid && ACTIVE.includes(d.status))
      .sort((a, b) => b.created - a.created)[0];

    const icon = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3v11m0 0-4.5-4.5M12 14l4.5-4.5M5 19h14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
    let label = "Baixar";
    if (active) {
      if (active.status === "processing") label = "Processando…";
      else if (active.percent != null) label = `${Math.floor(active.percent)}%`;
      else label = "Iniciando…";
    }
    button.innerHTML = `${icon}<span></span>`;
    button.querySelector("span").textContent = label;
    button.classList.toggle("ytb-busy", !!active);
    button.style.setProperty("--ytb-progress", active?.percent != null ? `${active.percent}%` : "0%");
  }

  function placeButton() {
    const vid = currentVideoId();
    if (!vid) {
      wrap?.remove();
      return;
    }
    if (!wrap) build();
    const isShorts = location.pathname.startsWith("/shorts/");
    if (isShorts) {
      if (!wrap.isConnected || !wrap.classList.contains("ytb-floating")) {
        wrap.classList.add("ytb-floating");
        document.body.appendChild(wrap);
      }
    } else {
      const anchor = ANCHORS.map((s) => document.querySelector(s)).find(Boolean);
      if (anchor) {
        if (wrap.parentElement !== anchor.parentElement || wrap.nextElementSibling !== anchor) {
          wrap.classList.remove("ytb-floating");
          anchor.parentElement.insertBefore(wrap, anchor);
        }
      } else if (!wrap.isConnected) {
        wrap.classList.add("ytb-floating");
        document.body.appendChild(wrap);
      }
    }
    render();
  }

  chrome.storage.local.get("downloads").then(({ downloads: d = {} }) => {
    downloads = d;
    render();
  });
  chrome.storage.onChanged.addListener((changes, area) => {
    if (area === "local" && changes.downloads) {
      downloads = changes.downloads.newValue || {};
      render();
    }
  });

  // O YouTube é uma SPA: reposiciona o botão a cada navegação e periodicamente,
  // porque a página às vezes recria a barra de ações.
  document.addEventListener("yt-navigate-finish", placeButton);
  setInterval(placeButton, 1500);
  placeButton();
})();
