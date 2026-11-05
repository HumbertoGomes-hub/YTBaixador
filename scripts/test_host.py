#!/usr/bin/env python3
"""Teste de fumaça do native host, conversando com ele pelo mesmo protocolo do navegador.

    python3 scripts/test_host.py                 # offline: ping + download de um vídeo local
    python3 scripts/test_host.py --online        # também consulta e baixa um vídeo do YouTube
    python3 scripts/test_host.py --host ~/.local/share/yt-baixador/ytdl_host.py

O teste offline gera um MP4 com ffmpeg, serve por HTTP em 127.0.0.1 e baixa com o
preset "best". Os arquivos baixados vão para uma pasta temporária e são apagados.
"""

import argparse
import functools
import http.server
import json
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

from common import HOST_SCRIPT

ONLINE_URL = "https://www.youtube.com/watch?v=jNQXAC9IVRw"  # "Me at the zoo", 19 s


class Host:
    def __init__(self, path):
        self.proc = subprocess.Popen([str(path)], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        self.messages = []
        self.cond = threading.Condition()
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        while True:
            head = self.proc.stdout.read(4)
            if len(head) < 4:
                return
            (n,) = struct.unpack("<I", head)
            msg = json.loads(self.proc.stdout.read(n))
            with self.cond:
                self.messages.append(msg)
                self.cond.notify_all()

    def send(self, msg):
        data = json.dumps(msg).encode()
        self.proc.stdin.write(struct.pack("<I", len(data)) + data)
        self.proc.stdin.flush()

    def wait_for(self, pred, timeout):
        deadline = time.monotonic() + timeout
        with self.cond:
            while True:
                for m in self.messages:
                    if pred(m):
                        return m
                left = deadline - time.monotonic()
                if left <= 0:
                    return None
                self.cond.wait(left)

    def close(self):
        self.proc.stdin.close()
        self.proc.wait(timeout=30)


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


failures = 0


def check(name, cond, detail=""):
    global failures
    print(f"  {'✓' if cond else '✗'} {name}{f' — {detail}' if detail else ''}")
    if not cond:
        failures += 1


def download(host, job_id, url, preset, outdir, timeout=180):
    host.send({"cmd": "download", "id": job_id, "url": url, "preset": preset, "outdir": str(outdir)})
    end = host.wait_for(lambda m: m.get("id") == job_id and m["type"] in ("done", "error", "cancelled"), timeout)
    progress = [m for m in host.messages if m.get("id") == job_id and m["type"] == "progress"]
    return end, progress


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=str(HOST_SCRIPT))
    ap.add_argument("--online", action="store_true")
    args = ap.parse_args()

    host = Host(Path(args.host).expanduser())
    tmp = Path(tempfile.mkdtemp(prefix="ytb-test-"))
    try:
        print("ping")
        host.send({"cmd": "ping"})
        pong = host.wait_for(lambda m: m["type"] == "pong", 30)
        check("host respondeu", pong is not None)
        if not pong:
            return
        check("yt-dlp encontrado", bool(pong.get("ytdlp")), f"{pong.get('ytdlp')} {pong.get('ytdlpVersion')}")
        check("ffmpeg encontrado", bool(pong.get("ffmpeg")), pong.get("ffmpeg") or "")
        check("runtime JavaScript encontrado", bool(pong.get("jsRuntime")), pong.get("jsRuntime") or "")

        print("download local (offline)")
        if shutil.which("ffmpeg") and pong.get("ytdlp"):
            srv_dir = tmp / "srv"
            srv_dir.mkdir()
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=320x240:rate=25",
                            "-f", "lavfi", "-i", "sine", "-t", "5", "-c:v", "libx264", "-preset", "ultrafast",
                            "-c:a", "aac", "-shortest", str(srv_dir / "teste.mp4")], check=True)
            handler = functools.partial(QuietHandler, directory=str(srv_dir))
            httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
            threading.Thread(target=httpd.serve_forever, daemon=True).start()
            url = f"http://127.0.0.1:{httpd.server_address[1]}/teste.mp4"
            end, progress = download(host, "local", url, "best", tmp / "out")
            httpd.shutdown()
            check("download concluído", end and end["type"] == "done", (end or {}).get("message", ""))
            check("progresso recebido", len(progress) > 0, f"{len(progress)} mensagens")
            check("arquivo existe", bool(end and end.get("file") and Path(end["file"]).is_file()))
        else:
            print("  ⚠ pulado (precisa de ffmpeg e yt-dlp)")

        if args.online:
            print("YouTube (online)")
            host.send({"cmd": "info", "reqId": "i1", "url": ONLINE_URL})
            info = host.wait_for(lambda m: m.get("reqId") == "i1", 120)
            check("info", bool(info and info.get("title")), (info or {}).get("title") or (info or {}).get("error", "timeout"))
            for preset in ("720", "mp3"):
                end, _ = download(host, f"yt-{preset}", ONLINE_URL, preset, tmp / "yt")
                ok = bool(end and end["type"] == "done" and Path(end.get("file") or "").is_file())
                check(f"download preset {preset}", ok, Path(end["file"]).name if ok else (end or {}).get("message", "timeout"))
    finally:
        host.close()
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    print("OK" if failures == 0 else f"FALHOU: {failures} verificação(ões)")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
