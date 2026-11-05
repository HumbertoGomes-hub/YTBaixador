"""Utilidades compartilhadas pelos scripts do projeto (só biblioteca padrão)."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXTENSION = ROOT / "extension"
HOST = ROOT / "host"
MANIFEST = EXTENSION / "manifest.json"
HOST_SCRIPT = HOST / "ytdl_host.py"
DIST = ROOT / "dist"
PROJECT = "yt-baixador"

HOST_VERSION_RE = re.compile(r'^HOST_VERSION = "([^"]+)"$', re.M)


def manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def extension_version():
    return manifest()["version"]


def host_version():
    m = HOST_VERSION_RE.search(HOST_SCRIPT.read_text(encoding="utf-8"))
    return m.group(1) if m else None
