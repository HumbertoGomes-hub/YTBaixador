#!/usr/bin/env bash
# Instala o "YT Baixador" (extensão + native host) para o usuário atual.
#
# Uso:
#   host/install.sh                 instala em ~/.local/share/yt-baixador e registra o host
#   EXT_ID=<id> host/install.sh --dev
#                                   registra o host direto da pasta do projeto (para desenvolver)
#   host/install.sh --no-download   não baixa yt-dlp/deno (usa os que já existem no sistema)
#   host/install.sh --update-tools  baixa de novo yt-dlp e deno mesmo que já existam
#   host/install.sh --uninstall     remove o registro do host e a pasta instalada
#
# Cada instalação gera o próprio ID de extensão: uma chave pública aleatória é criada
# na primeira execução, guardada em $PREFIX/manifest-key.txt e reaproveitada nas
# atualizações. A chave privada nunca é gravada em disco.
#
# Variáveis de ambiente:
#   PREFIX   pasta de instalação (padrão: ~/.local/share/yt-baixador)
#   EXT_ID   ID da extensão permitida (obrigatório com --dev; ignora a chave gerada)
set -euo pipefail

HOST_NAME="com.ytbaixador.host"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$HERE")"
PREFIX="${PREFIX:-${XDG_DATA_HOME:-$HOME/.local/share}/yt-baixador}"

MODE="install"
DOWNLOAD="missing"   # missing | always | never
for arg in "$@"; do
  case "$arg" in
    --dev) MODE="dev" ;;
    --uninstall) MODE="uninstall" ;;
    --no-download) DOWNLOAD="never" ;;
    --update-tools) DOWNLOAD="always" ;;
    -h|--help) sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Opção desconhecida: $arg (use --help)" >&2; exit 2 ;;
  esac
done

BROWSER_DIRS=(
  "$HOME/.config/google-chrome"
  "$HOME/.config/google-chrome-beta"
  "$HOME/.config/google-chrome-unstable"
  "$HOME/.config/chromium"
  "$HOME/.config/BraveSoftware/Brave-Browser"
  "$HOME/.config/microsoft-edge"
  "$HOME/.config/vivaldi"
)

# ------------------------------------------------------------------ remover

if [ "$MODE" = "uninstall" ]; then
  for d in "${BROWSER_DIRS[@]}"; do
    f="$d/NativeMessagingHosts/$HOST_NAME.json"
    [ -f "$f" ] && rm -f "$f" && echo "✓ Removido de $d"
  done
  if [ -d "$PREFIX" ]; then
    rm -rf "$PREFIX" && echo "✓ Pasta $PREFIX removida"
  fi
  echo "Host desinstalado. Remova a extensão pela página de extensões do navegador."
  exit 0
fi

# ------------------------------------------------------------ pré-requisitos

command -v python3 >/dev/null 2>&1 || { echo "Erro: python3 não encontrado." >&2; exit 1; }

EXT_DIR=""
if [ "$MODE" = "dev" ]; then
  if [ -z "${EXT_ID:-}" ]; then
    cat >&2 <<EOF
Erro: no modo --dev, informe o ID da extensão carregada a partir de $ROOT/extension:
  1. chrome://extensions → Modo do desenvolvedor → Carregar sem compactação → $ROOT/extension
  2. copie o ID mostrado no card da extensão
  3. EXT_ID=<id> $0 --dev
EOF
    exit 1
  fi
  TARGET="$HERE"
else
  TARGET="$PREFIX"
  mkdir -p "$TARGET"
  install -m 755 "$HERE/ytdl_host.py" "$TARGET/ytdl_host.py"
  echo "✓ Host copiado para $TARGET"

  # Chave pública desta instalação: gerada uma vez, reaproveitada nas atualizações
  # para o ID (e os dados salvos da extensão) continuarem os mesmos.
  KEY_FILE="$TARGET/manifest-key.txt"
  if [ ! -s "$KEY_FILE" ]; then
    command -v openssl >/dev/null 2>&1 || { echo "Erro: openssl não encontrado (sudo apt install openssl)." >&2; exit 1; }
    openssl genrsa 2048 2>/dev/null | openssl rsa -pubout -outform DER 2>/dev/null | base64 -w0 > "$KEY_FILE.tmp"
    [ -s "$KEY_FILE.tmp" ] || { echo "Erro: falha ao gerar a chave da extensão." >&2; exit 1; }
    mv "$KEY_FILE.tmp" "$KEY_FILE"
    echo "✓ ID de extensão exclusivo desta instalação gerado"
  fi

  # Copia a extensão para a pasta instalada e grava a chave no manifest da cópia.
  EXT_DIR="$TARGET/extension"
  rm -rf "$EXT_DIR.tmp"
  cp -r "$ROOT/extension" "$EXT_DIR.tmp"
  GEN_ID="$(python3 - "$EXT_DIR.tmp/manifest.json" "$KEY_FILE" <<'PY'
import base64, hashlib, json, sys
manifest_path, key_path = sys.argv[1], sys.argv[2]
key = open(key_path, encoding="ascii").read().strip()
with open(manifest_path, encoding="utf-8") as f:
    manifest = json.load(f)
manifest["key"] = key
with open(manifest_path, "w", encoding="utf-8") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=2)
    f.write("\n")
digest = hashlib.sha256(base64.b64decode(key)).hexdigest()[:32]
print("".join(chr(ord("a") + int(c, 16)) for c in digest))
PY
)"
  rm -rf "$EXT_DIR" && mv "$EXT_DIR.tmp" "$EXT_DIR"
  echo "✓ Extensão copiada para $EXT_DIR"
  EXT_ID="${EXT_ID:-$GEN_ID}"
fi
HOST_SCRIPT="$TARGET/ytdl_host.py"
BIN="$TARGET/bin"

# --------------------------------------------------------------- ferramentas

fetch() { # url destino
  curl -fL --progress-bar --retry 3 -o "$2" "$1"
}

download_ytdlp() {
  local asset="yt-dlp_linux"
  [ "$(uname -m)" = "aarch64" ] && asset="yt-dlp_linux_aarch64"
  echo "→ Baixando yt-dlp (github.com/yt-dlp/yt-dlp)…"
  fetch "https://github.com/yt-dlp/yt-dlp/releases/latest/download/$asset" "$BIN/yt-dlp.tmp"
  chmod 755 "$BIN/yt-dlp.tmp" && mv "$BIN/yt-dlp.tmp" "$BIN/yt-dlp"
}

download_deno() {
  local asset="deno-x86_64-unknown-linux-gnu.zip" tmp
  [ "$(uname -m)" = "aarch64" ] && asset="deno-aarch64-unknown-linux-gnu.zip"
  echo "→ Baixando deno (github.com/denoland/deno), runtime JavaScript exigido pelo yt-dlp…"
  tmp="$(mktemp -d)"
  fetch "https://github.com/denoland/deno/releases/latest/download/$asset" "$tmp/deno.zip"
  python3 -c "import sys, zipfile; zipfile.ZipFile(sys.argv[1]).extract('deno', sys.argv[2])" "$tmp/deno.zip" "$tmp"
  install -m 755 "$tmp/deno" "$BIN/deno"
  rm -rf "$tmp"
}

# Reaproveita binários já baixados em host/bin (ex.: instalação anterior em modo --dev).
if [ "$TARGET" != "$HERE" ] && [ "$DOWNLOAD" != "always" ]; then
  for tool in yt-dlp deno; do
    if [ -x "$HERE/bin/$tool" ] && [ ! -x "$BIN/$tool" ]; then
      mkdir -p "$BIN" && install -m 755 "$HERE/bin/$tool" "$BIN/$tool"
      echo "✓ $tool copiado de $HERE/bin"
    fi
  done
fi

if [ "$DOWNLOAD" != "never" ]; then
  command -v curl >/dev/null 2>&1 || { echo "Erro: curl não encontrado (sudo apt install curl)." >&2; exit 1; }
  mkdir -p "$BIN"
  if [ "$DOWNLOAD" = "always" ] || [ ! -x "$BIN/yt-dlp" ]; then
    download_ytdlp
  else
    echo "✓ yt-dlp já instalado ($("$BIN/yt-dlp" --version 2>/dev/null || echo '?'))"
  fi
  if [ -x "$BIN/deno" ] && [ "$DOWNLOAD" != "always" ]; then
    echo "✓ deno já instalado"
  elif [ ! -x "$BIN/deno" ] && { command -v deno >/dev/null 2>&1 || command -v node >/dev/null 2>&1; }; then
    echo "✓ Runtime JavaScript do sistema encontrado ($(command -v deno || command -v node))"
  else
    download_deno
  fi
fi

# ------------------------------------------------------------------ registro

MANIFEST=$(cat <<EOF
{
  "name": "$HOST_NAME",
  "description": "YT Baixador native host (yt-dlp)",
  "path": "$HOST_SCRIPT",
  "type": "stdio",
  "allowed_origins": ["chrome-extension://$EXT_ID/"]
}
EOF
)

count=0
for d in "${BROWSER_DIRS[@]}"; do
  if [ -d "$d" ]; then
    mkdir -p "$d/NativeMessagingHosts"
    printf '%s\n' "$MANIFEST" > "$d/NativeMessagingHosts/$HOST_NAME.json"
    echo "✓ Registrado em $d"
    count=$((count + 1))
  fi
done
if [ "$count" -eq 0 ]; then
  echo "⚠ Nenhum navegador Chromium encontrado em ~/.config. Abra o navegador uma vez e rode de novo." >&2
fi

command -v ffmpeg >/dev/null 2>&1 \
  || echo "⚠ ffmpeg não encontrado: instale-o (sudo apt install ffmpeg) para juntar vídeo+áudio e gerar MP3."

echo
echo "Host:          $HOST_SCRIPT"
echo "ID permitido:  $EXT_ID"
if [ -n "$EXT_DIR" ]; then
  echo
  echo "Pronto! Agora, no navegador:"
  echo "  1. Abra chrome://extensions (ou brave://, edge://, vivaldi://) e ative o Modo do desenvolvedor."
  echo "  2. Clique em 'Carregar sem compactação' e escolha a pasta:"
  echo "       $EXT_DIR"
  echo "  3. Confira se o ID no card da extensão é $EXT_ID e reinicie o navegador."
  echo "Em atualizações, basta rodar este instalador de novo e clicar em ↻ no card da extensão."
else
  echo "Pronto! Recarregue a extensão em chrome://extensions."
fi
