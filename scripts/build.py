#!/usr/bin/env python3
"""Gera os pacotes de release em dist/.

    python3 scripts/build.py            # roda check.py antes
    python3 scripts/build.py --skip-check

Saída (X.Y.Z = versão do manifest):
  dist/yt-baixador-X.Y.Z-linux.tar.gz    pacote completo para o usuário final
                                         (extensão + host + instalador + docs)
  dist/SHA256SUMS                        checksum do pacote
"""

import hashlib
import io
import subprocess
import sys
import tarfile
import time

from common import DIST, HOST, PROJECT, ROOT, extension_version

# Arquivos que entram no pacote completo (relativos à raiz do projeto).
BUNDLE = [
    "extension",
    "host/ytdl_host.py",
    "host/install.sh",
    "README.md",
    "CHANGELOG.md",
    "docs",
]
EXECUTABLE = {"host/ytdl_host.py", "host/install.sh"}
IGNORE_NAMES = {".DS_Store", "__pycache__", "host.log"}


def files_of(rel):
    path = ROOT / rel
    if path.is_file():
        yield path
    else:
        for p in sorted(path.rglob("*")):
            if p.is_file() and not any(part in IGNORE_NAMES for part in p.parts):
                yield p


def build_tarball(version):
    prefix = f"{PROJECT}-{version}"
    out = DIST / f"{prefix}-linux.tar.gz"
    mtime = int(time.time())
    with tarfile.open(out, "w:gz") as tar:
        for rel in BUNDLE:
            if not (ROOT / rel).exists():
                sys.exit(f"Erro: {rel} não existe")
            for f in files_of(rel):
                arc = f.relative_to(ROOT).as_posix()
                info = tarfile.TarInfo(f"{prefix}/{arc}")
                data = f.read_bytes()
                info.size = len(data)
                info.mtime = mtime
                info.mode = 0o755 if arc in EXECUTABLE else 0o644
                tar.addfile(info, io.BytesIO(data))
    return out



def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if "--skip-check" not in sys.argv:
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "check.py")])
        if r.returncode != 0:
            sys.exit("Build cancelado: corrija os erros do check.")
        print()

    version = extension_version()
    DIST.mkdir(exist_ok=True)
    for old in DIST.glob(f"{PROJECT}-*{version}*"):
        old.unlink()

    artifacts = [build_tarball(version)]
    sums = DIST / "SHA256SUMS"
    sums.write_text("".join(f"{sha256(a)}  {a.name}\n" for a in artifacts), encoding="utf-8")

    print(f"Release {version}:")
    for a in [*artifacts, sums]:
        print(f"  {a.relative_to(ROOT)}  ({a.stat().st_size / 1024:.0f} KB)")
    if (HOST / "bin").exists():
        print("  (host/bin não é incluído: o instalador baixa yt-dlp e deno na máquina do usuário)")


if __name__ == "__main__":
    main()
