#!/usr/bin/env python3
"""Verificações estáticas antes de um release.

    python3 scripts/check.py

Confere: manifest válido, arquivos referenciados existem, versões da extensão e do
host batem, Python e shell sem erro de sintaxe e, se houver deno, lint do JavaScript.
"""

import re
import shutil
import subprocess
import sys
from pathlib import Path

from common import EXTENSION, HOST, HOST_SCRIPT, ROOT, extension_version, host_version, manifest

errors = []
warnings = []


def ok(msg):
    print(f"  ✓ {msg}")


def fail(msg):
    errors.append(msg)
    print(f"  ✗ {msg}")


def warn(msg):
    warnings.append(msg)
    print(f"  ⚠ {msg}")


print("Manifest")
try:
    m = manifest()
    ok(f"manifest.json válido (MV{m.get('manifest_version')}, versão {m['version']})")
    referenced = set()
    referenced.update(m.get("icons", {}).values())
    referenced.update(m.get("action", {}).get("default_icon", {}).values())
    if m.get("action", {}).get("default_popup"):
        referenced.add(m["action"]["default_popup"])
    if m.get("background", {}).get("service_worker"):
        referenced.add(m["background"]["service_worker"])
    for cs in m.get("content_scripts", []):
        referenced.update(cs.get("js", []))
        referenced.update(cs.get("css", []))
    missing = [f for f in sorted(referenced) if not (EXTENSION / f).is_file()]
    if missing:
        fail("arquivos referenciados que não existem: " + ", ".join(missing))
    else:
        ok(f"{len(referenced)} arquivos referenciados existem")
    if "key" in m:
        fail("manifest.json tem 'key': o ID é gerado por instalação (install.sh); remova o campo")
    else:
        ok("manifest sem 'key' (cada instalação gera o próprio ID)")
except Exception as e:  # noqa: BLE001
    fail(f"manifest.json inválido: {e}")

print("Versões")
ev, hv = extension_version(), host_version()
if ev == hv:
    ok(f"extensão e host na versão {ev}")
else:
    fail(f"versões diferentes: extensão {ev}, host {hv} (use scripts/bump_version.py)")
changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8") if (ROOT / "CHANGELOG.md").exists() else ""
if f"## [{ev}]" in changelog:
    ok(f"CHANGELOG.md tem a seção [{ev}]")
else:
    warn(f"CHANGELOG.md não tem a seção [{ev}]")

print("Python e shell")
for py in [HOST_SCRIPT, *sorted((ROOT / "scripts").glob("*.py"))]:
    try:
        compile(py.read_text(encoding="utf-8"), str(py), "exec")
        ok(py.relative_to(ROOT).as_posix())
    except SyntaxError as e:
        fail(f"{py.name}:{e.lineno}: {e.msg}")
for sh in [HOST / "install.sh"]:
    r = subprocess.run(["bash", "-n", str(sh)], capture_output=True, text=True)
    (ok if r.returncode == 0 else fail)(f"{sh.relative_to(ROOT)} {r.stderr.strip()}".strip())

print("JavaScript")
deno_candidates = [HOST / "bin" / "deno", Path.home() / ".local/share/yt-baixador/bin/deno"]
deno = shutil.which("deno") or next((str(p) for p in deno_candidates if p.exists()), None)
if deno:
    r = subprocess.run([deno, "lint", "--quiet", str(EXTENSION)], capture_output=True, text=True)
    if r.returncode == 0:
        ok("deno lint sem problemas")
    else:
        fail("deno lint encontrou problemas:\n" + (r.stdout + r.stderr).strip())
elif shutil.which("node"):
    for js in sorted(EXTENSION.glob("*.js")):
        r = subprocess.run(["node", "--check", str(js)], capture_output=True, text=True)
        (ok if r.returncode == 0 else fail)(f"{js.name} {r.stderr.strip()}".strip())
else:
    warn("nem deno nem node encontrados: JavaScript não verificado")

print("Segredos e dados locais")
# Arquivos que entrariam num commit: os rastreados e os novos que o .gitignore não exclui.
# Fora de um repositório git, varre tudo menos o que o .gitignore costuma excluir.
SKIP_DIRS = {".git", "dist", "__pycache__", "bin"}
r = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
                   cwd=ROOT, capture_output=True)
if r.returncode == 0:
    candidates = [ROOT / p for p in r.stdout.decode().split("\0") if p and (ROOT / p).is_file()]
else:
    candidates = [p for p in ROOT.rglob("*")
                  if p.is_file() and not SKIP_DIRS.intersection(p.relative_to(ROOT).parts)]

if not (ROOT / ".gitignore").is_file():
    fail(".gitignore não existe")
private_key = re.compile(rb"-----BEGIN (RSA |EC |OPENSSH |ENCRYPTED )?" + rb"PRIVATE KEY-----")
home_path = re.compile(rb"/home/(?!user\b)[a-z_][a-z0-9_-]*")
found = 0
for p in candidates:
    rel = p.relative_to(ROOT).as_posix()
    if p.suffix in (".pem", ".key", ".log") or rel.startswith(("keys/", "host/bin/", "dist/")):
        fail(f"{rel}: não deve ir para o repositório")
        found += 1
        continue
    if p.stat().st_size > 5 * 1024 * 1024:
        fail(f"{rel}: arquivo grande ({p.stat().st_size // 1024 // 1024} MB)")
        found += 1
        continue
    data = p.read_bytes()
    if private_key.search(data):
        fail(f"{rel}: contém uma chave privada")
        found += 1
    m = home_path.search(data)
    if m:
        fail(f"{rel}: contém um caminho da sua máquina ({m.group().decode(errors='replace')})")
        found += 1
if not found:
    ok(f"{len(candidates)} arquivos sem chaves, logs ou caminhos locais")

# Ignorados pelo git, mas presentes na pasta: um upload pelo site do GitHub os enviaria.
present = sorted(p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*")
                 if p.is_file() and ".git" not in p.relative_to(ROOT).parts
                 and (p.suffix in (".pem", ".key", ".log") or p.relative_to(ROOT).parts[0] in ("keys", "dist")
                      or p.relative_to(ROOT).as_posix().startswith("host/bin/")))
if present:
    warn("na pasta, ignorados pelo git (envie com git push, não pelo site): " + ", ".join(present))

print()
if errors:
    print(f"FALHOU: {len(errors)} erro(s), {len(warnings)} aviso(s)")
    sys.exit(1)
print(f"OK ({len(warnings)} aviso(s))")
