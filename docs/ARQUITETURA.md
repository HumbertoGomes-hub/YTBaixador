# Arquitetura

## Visão geral

```
┌──────────────── Navegador ─────────────────┐        ┌──────────── Sistema ─────────────┐
│                                            │        │                                  │
│  content.js ──┐                            │ stdio  │  ytdl_host.py ──▶ yt-dlp ──▶ ffmpeg
│  (YouTube)    │ runtime.sendMessage        │ (JSON) │       │             │            │
│               ▼                            │        │       │             ▼            │
│  popup.js ──▶ background.js ◀── connectNative ─────▶│       │       YouTube (HTTPS)    │
│               │   (service worker)         │        │       │                          │
│               ▼                            │        │       ▼                          │
│        chrome.storage.local ──onChanged──▶ content.js / popup.js     ~/Downloads/…     │
└────────────────────────────────────────────┘        └──────────────────────────────────┘
```

### Por que um native host?

O YouTube não entrega URLs diretas de vídeo. Os links são protegidos por assinaturas embaralhadas e pelo parâmetro `n`, calculados por um JavaScript que muda com frequência. Também há tokens de prova (PO tokens) e streaming segmentado. O yt-dlp resolve tudo isso e é atualizado em poucos dias quando o YouTube muda algo. Reimplementar essa lógica dentro da extensão seria frágil. Além disso, juntar vídeo e áudio exige ffmpeg, que não roda no navegador sem um WASM pesado.

Por isso a extensão é só interface. O trabalho fica com o yt-dlp, chamado via [native messaging](https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging).

## Componentes

### `extension/manifest.json`
- Manifest V3.
- Permissões: `nativeMessaging` (falar com o host), `storage` (estado e configurações), `tabs` (URL e título da aba no popup), `notifications` (aviso ao terminar).
- `host_permissions` e `content_scripts` restritos a `www.youtube.com` e `m.youtube.com`.
- **Sem `key` no repositório.** O `install.sh` gera uma chave pública RSA aleatória na primeira instalação, guarda em `~/.local/share/yt-baixador/manifest-key.txt` e grava no `manifest.json` da cópia instalada. É ela que fixa o ID da extensão naquela máquina. A chave privada é descartada na hora: ela só seria necessária para assinar um `.crx`, e extensões carregadas sem compactação não precisam disso. Cada instalação tem um ID diferente, e o registro do host só aceita esse ID (`allowed_origins`).

### `extension/background.js` (service worker)
- Mantém **uma** conexão com o host (`chrome.runtime.connectNative`). Uma porta nativa aberta mantém o service worker vivo (Chrome 105+), então o progresso continua chegando enquanto o download roda.
- Recebe comandos de `content.js` e `popup.js` via `chrome.runtime.onMessage`.
- Normaliza URLs (`watch`, `youtu.be`, `shorts`, `live`, `embed`) para `https://www.youtube.com/watch?v=ID`, o que descarta parâmetros de playlist.
- Guarda o estado dos downloads em `chrome.storage.local` (chave `downloads`, no máximo 30). As atualizações de progresso são agrupadas a cada 300 ms.
- Mostra notificações em `done` e `error`.

### `extension/content.js` / `content.css`
- Injeta o botão antes de `ytd-watch-metadata #top-level-buttons-computed` (com alternativas). Nos Shorts, ou se não achar a barra, usa um botão flutuante.
- O YouTube é uma SPA: reposiciona o botão no evento `yt-navigate-finish` e a cada 1,5 s, porque a página recria a barra de ações.
- Não fala com o host. Lê o progresso por `chrome.storage.onChanged`.
- Usa as variáveis de CSS do YouTube (`--yt-spec-*`), então segue o tema claro/escuro.

### `extension/popup.*`
- Mostra o vídeo da aba ativa e pede detalhes ao host (`info`).
- Lista os downloads a partir de `chrome.storage.local` e reage a mudanças.
- Configurações em `chrome.storage.local` → `settings`: `{ outdir, preset }`.

### `host/ytdl_host.py`
- Python 3, só biblioteca padrão.
- Lê mensagens do stdin e responde no stdout. Cada download roda em uma thread que acompanha um subprocesso do yt-dlp.
- Acha o yt-dlp em `bin/` ao lado do script ou no `PATH`. Coloca `bin/`, `~/.deno/bin` e `~/.local/bin` no `PATH` do subprocesso, para o yt-dlp achar o deno.
- Se o stdin fechar (navegador fechado), os downloads em andamento continuam até o fim e o processo sai depois.
- Grava um log em `host.log` ao lado do script.

### `host/install.sh`
- Copia o host e a extensão para `~/.local/share/yt-baixador` (ou registra o host no lugar com `--dev`, usando o `EXT_ID` informado).
- Baixa `yt-dlp` e `deno` para `bin/`.
- Gera (ou reaproveita) a chave da instalação, calcula o ID e grava `com.ytbaixador.host.json` em `~/.config/<navegador>/NativeMessagingHosts/`.

## Protocolo do native host

Cada mensagem é um JSON em UTF-8 precedido do tamanho em 4 bytes (uint32 little-endian), como define o protocolo de native messaging do Chrome. Uma mensagem do host para o navegador pode ter no máximo 1 MB.

### Extensão → host

| `cmd` | Campos | Resposta |
|---|---|---|
| `ping` | — | `pong` |
| `info` | `reqId`, `url` | `info` com o mesmo `reqId` |
| `download` | `id`, `url`, `preset`, `outdir` (vazio = Downloads) | `started`, vários `progress`, depois `done` / `error` / `cancelled` |
| `cancel` | `id` | o download em andamento termina com `cancelled` |
| `open` | `path` (arquivo ou pasta; vazio = Downloads) | nenhuma; abre com `xdg-open` |
| `update` | `reqId` | `update` com o mesmo `reqId` |

### Host → extensão

```jsonc
{"type": "pong", "hostVersion": "1.0.0", "ytdlp": "/…/bin/yt-dlp", "ytdlpVersion": "2026.10.26",
 "ffmpeg": "/usr/bin/ffmpeg", "jsRuntime": "/…/bin/deno", "defaultOutdir": "/home/user/Downloads"}

{"type": "info", "reqId": "…", "title": "…", "uploader": "…", "duration": 19,
 "thumbnail": "https://…", "heights": [1080, 720, 480, 360, 240]}
{"type": "info", "reqId": "…", "error": "mensagem"}

{"type": "started",   "id": "…", "outdir": "/home/user/Downloads"}
{"type": "progress",  "id": "…", "part": 1, "status": "downloading", "percent": 42.3,
 "speed": 2162686.8, "eta": 12, "total": 629172}
{"type": "progress",  "id": "…", "part": 1, "status": "processing", "percent": 100.0, …}
{"type": "done",      "id": "…", "file": "/home/user/Downloads/Título [ID].mp4", "outdir": "…"}
{"type": "error",     "id": "…", "message": "[youtube] …: Video unavailable"}
{"type": "cancelled", "id": "…"}

{"type": "update", "reqId": "…", "ok": true, "version": "2026.10.26", "output": "…"}
```

- `part` aumenta a cada stream baixado: com vídeo e áudio separados, a parte 1 é o vídeo e a 2 é o áudio.
- `status: "processing"` indica que o stream terminou. Depois disso vem a próxima parte ou o pós-processamento (junção ou conversão pelo ffmpeg).
- `percent`, `speed`, `eta` e `total` podem ser `null` quando o yt-dlp não sabe o valor.

### Como o progresso é lido

O host roda o yt-dlp com `--newline --progress --progress-template` e um modelo separado por tabs com o prefixo `PROG\t`. O caminho final do arquivo vem de `--print after_move:FILE\t%(filepath)s`. Qualquer outra linha da saída padrão vai para o log. O stderr é guardado (últimas 50 linhas), e a última linha `ERROR:` vira a mensagem de erro.

## Presets → argumentos do yt-dlp

| Preset | Argumentos |
|---|---|
| `best` | `-f bv*+ba/b --merge-output-format mp4/mkv` |
| `1080` / `720` / `480` | `-S res:N,vcodec:h264,acodec:m4a -f bv*+ba/b --merge-output-format mp4` |
| `mp3` | `-f ba/b -x --audio-format mp3 --audio-quality 0 --embed-thumbnail --embed-metadata` |
| `m4a` | `-f ba[ext=m4a]/ba/b -x --audio-format m4a --embed-thumbnail --embed-metadata` |

Argumentos comuns a todos: `--no-playlist --color never --no-warnings -P <outdir> -o "%(title)s [%(id)s].%(ext)s"`. Se não houver deno, mas houver node ou bun, e o yt-dlp for 2025.11 ou mais novo, o host adiciona `--js-runtimes node` (ou `bun`).

## Estado de um download

```
queued ──started──▶ downloading ⇄ processing ──▶ done
   │                     │                    └──▶ error
   │                     └──cancel──▶ cancelled
   └──host indisponível──▶ error
downloading/processing ──worker reiniciou ou host caiu──▶ unknown
```

Registro em `chrome.storage.local.downloads[id]`:

```jsonc
{ "id": "uuid", "videoId": "jNQXAC9IVRw", "url": "https://www.youtube.com/watch?v=…",
  "title": "…", "preset": "720", "status": "downloading", "percent": 42.3,
  "speed": 2162686.8, "eta": 12, "part": 1, "outdir": "…", "file": "…", "error": "…",
  "created": 1762368000000, "updated": 1762368005000 }
```

## Segurança

- O host só aceita conexões da extensão com o ID listado em `allowed_origins`. O navegador garante isso. Como o ID é aleatório e diferente em cada máquina, outra extensão não tem como saber de antemão qual ID imitar.
- O host não abre nenhuma porta de rede: só fala com o navegador pelo stdin/stdout de um processo que o próprio navegador inicia.
- O host não usa shell: o yt-dlp é chamado com uma lista de argumentos, e a URL vem depois de `--`, então não pode ser lida como opção.
- A extensão só manda URLs normalizadas `https://www.youtube.com/watch?v=<id>`.
- `open` só abre caminhos que existem, com `xdg-open`.
- `update` só atualiza o yt-dlp que fica na pasta `bin/` do host, nunca o do sistema.
- O instalador baixa binários só dos releases oficiais no GitHub (`yt-dlp/yt-dlp` e `denoland/deno`), por HTTPS.
