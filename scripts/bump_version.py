#!/usr/bin/env python3
"""Atualiza a versão da extensão e do host de uma vez.

    python3 scripts/bump_version.py 1.1.0

Altera extension/manifest.json e HOST_VERSION em host/ytdl_host.py e cria uma
seção vazia no CHANGELOG.md, se ainda não existir.
"""

import datetime
import re
import sys

from common import HOST_SCRIPT, HOST_VERSION_RE, MANIFEST, ROOT, extension_version

if len(sys.argv) != 2 or not re.fullmatch(r"\d+\.\d+\.\d+", sys.argv[1]):
    sys.exit("Uso: scripts/bump_version.py X.Y.Z")
new = sys.argv[1]
old = extension_version()

text = MANIFEST.read_text(encoding="utf-8")
text, n = re.subn(r'("version":\s*")[^"]+(")', rf"\g<1>{new}\g<2>", text, count=1)
if n != 1:
    sys.exit("Não achei o campo version no manifest.json")
MANIFEST.write_text(text, encoding="utf-8")

host = HOST_SCRIPT.read_text(encoding="utf-8")
host, n = HOST_VERSION_RE.subn(f'HOST_VERSION = "{new}"', host)
if n != 1:
    sys.exit("Não achei HOST_VERSION em ytdl_host.py")
HOST_SCRIPT.write_text(host, encoding="utf-8")

changelog = ROOT / "CHANGELOG.md"
if changelog.exists():
    content = changelog.read_text(encoding="utf-8")
    if f"## [{new}]" not in content:
        today = datetime.date.today().isoformat()
        section = f"## [{new}] - {today}\n\n### Adicionado\n\n### Alterado\n\n### Corrigido\n\n"
        idx = content.find("## [")
        content = content[:idx] + section + content[idx:] if idx >= 0 else content + "\n" + section
        changelog.write_text(content, encoding="utf-8")

print(f"Versão {old} → {new}. Preencha o CHANGELOG.md antes do build.")
