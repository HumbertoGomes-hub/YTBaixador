#!/usr/bin/env python3
"""Native messaging host for the "YT Baixador" extension.

The browser starts this script and talks to it over stdin/stdout using the
native messaging protocol (4-byte little-endian length + UTF-8 JSON).
Downloads are done by the yt-dlp executable, run as a subprocess.

Requests (extension -> host):
  {"cmd": "ping"}
  {"cmd": "info", "reqId": "...", "url": "..."}
  {"cmd": "download", "id": "...", "url": "...", "preset": "best", "outdir": ""}
  {"cmd": "cancel", "id": "..."}
  {"cmd": "open", "path": "..."}
  {"cmd": "update", "reqId": "..."}

Messages (host -> extension) always carry a "type" field.
"""

import json
import os
import shutil
import signal
import struct
import subprocess
import sys
import threading
import time

HOST_VERSION = "1.0.0"
HERE = os.path.dirname(os.path.abspath(__file__))
LOCAL_BIN = os.path.join(HERE, "bin")
LOG_FILE = os.path.join(HERE, "host.log")

_write_lock = threading.Lock()
_jobs = {}  # id -> subprocess.Popen
_jobs_lock = threading.Lock()


# --------------------------------------------------------------------------- io

def log(*parts):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + " ".join(str(p) for p in parts) + "\n")
    except OSError:
        pass


def send(msg):
    data = json.dumps(msg, ensure_ascii=False).encode("utf-8")
    with _write_lock:
        try:
            sys.stdout.buffer.write(struct.pack("<I", len(data)) + data)
            sys.stdout.buffer.flush()
        except (BrokenPipeError, OSError, ValueError):
            pass  # browser went away; keep the download running anyway


def read_message():
    raw_len = sys.stdin.buffer.read(4)
    if len(raw_len) < 4:
        return None
    (length,) = struct.unpack("<I", raw_len)
    data = sys.stdin.buffer.read(length)
    return json.loads(data.decode("utf-8"))


# ---------------------------------------------------------------- environment

def child_env():
    env = dict(os.environ)
    paths = [LOCAL_BIN, os.path.expanduser("~/.deno/bin"), os.path.expanduser("~/.local/bin"),
             "/usr/local/bin", "/usr/bin", "/bin"]
    env["PATH"] = os.pathsep.join(paths + [env.get("PATH", "")])
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def find_ytdlp():
    local = os.path.join(LOCAL_BIN, "yt-dlp")
    if os.access(local, os.X_OK):
        return local
    return shutil.which("yt-dlp", path=child_env()["PATH"])


_version_cache = {}


def ytdlp_version(exe):
    if exe not in _version_cache:
        try:
            out = subprocess.run([exe, "--version"], capture_output=True, text=True,
                                 timeout=30, env=child_env())
            _version_cache[exe] = out.stdout.strip()
        except Exception as e:  # noqa: BLE001
            log("version check failed:", e)
            _version_cache[exe] = ""
    return _version_cache[exe]


def base_args(exe):
    """Arguments shared by every yt-dlp call."""
    args = [exe, "--no-playlist", "--color", "never", "--no-warnings"]
    # yt-dlp >= 2025.11 needs a JavaScript runtime for YouTube. Deno is used
    # automatically when it is on PATH; otherwise fall back to node/bun.
    version = ytdlp_version(exe)
    path = child_env()["PATH"]
    if version >= "2025.11" and not shutil.which("deno", path=path):
        for rt in ("node", "bun"):
            if shutil.which(rt, path=path):
                args += ["--js-runtimes", rt]
                break
    return args


def default_outdir():
    try:
        out = subprocess.run(["xdg-user-dir", "DOWNLOAD"], capture_output=True, text=True, timeout=5)
        d = out.stdout.strip()
        if d and os.path.isdir(d):
            return d
    except Exception:  # noqa: BLE001
        pass
    return os.path.expanduser("~/Downloads")


PRESETS = {
    "best": ["-f", "bv*+ba/b", "--merge-output-format", "mp4/mkv"],
    "1080": ["-S", "res:1080,vcodec:h264,acodec:m4a", "-f", "bv*+ba/b", "--merge-output-format", "mp4"],
    "720": ["-S", "res:720,vcodec:h264,acodec:m4a", "-f", "bv*+ba/b", "--merge-output-format", "mp4"],
    "480": ["-S", "res:480,vcodec:h264,acodec:m4a", "-f", "bv*+ba/b", "--merge-output-format", "mp4"],
    "mp3": ["-f", "ba/b", "-x", "--audio-format", "mp3", "--audio-quality", "0",
            "--embed-thumbnail", "--embed-metadata"],
    "m4a": ["-f", "ba[ext=m4a]/ba/b", "-x", "--audio-format", "m4a",
            "--embed-thumbnail", "--embed-metadata"],
}

PROGRESS_PREFIX = "PROG\t"
FILE_PREFIX = "FILE\t"
PROGRESS_TEMPLATE = ("download:" + PROGRESS_PREFIX +
                     "%(progress.status)s\t%(progress.downloaded_bytes)s\t%(progress.total_bytes)s\t"
                     "%(progress.total_bytes_estimate)s\t%(progress.speed)s\t%(progress.eta)s\t"
                     "%(info.format_id)s")


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def last_error(stderr_lines):
    for line in reversed(stderr_lines):
        if line.startswith("ERROR:"):
            return line[len("ERROR:"):].strip()
    return stderr_lines[-1].strip() if stderr_lines else "yt-dlp terminou com erro"


# ------------------------------------------------------------------- commands

def cmd_ping(_msg):
    exe = find_ytdlp()
    path = child_env()["PATH"]
    send({
        "type": "pong",
        "hostVersion": HOST_VERSION,
        "ytdlp": exe,
        "ytdlpVersion": ytdlp_version(exe) if exe else None,
        "ffmpeg": shutil.which("ffmpeg", path=path),
        "jsRuntime": next((shutil.which(r, path=path) for r in ("deno", "node", "bun")
                           if shutil.which(r, path=path)), None),
        "defaultOutdir": default_outdir(),
    })


def cmd_info(msg):
    req = msg.get("reqId")
    exe = find_ytdlp()
    if not exe:
        send({"type": "info", "reqId": req, "error": "yt-dlp não encontrado. Rode host/install.sh."})
        return
    try:
        out = subprocess.run(base_args(exe) + ["-J", "--", msg["url"]], capture_output=True,
                             text=True, timeout=120, env=child_env())
        if out.returncode != 0:
            send({"type": "info", "reqId": req, "error": last_error(out.stderr.splitlines())})
            return
        data = json.loads(out.stdout)
        heights = sorted({f.get("height") for f in data.get("formats", [])
                          if f.get("height") and f.get("vcodec") not in (None, "none")}, reverse=True)
        send({
            "type": "info", "reqId": req,
            "title": data.get("title"),
            "uploader": data.get("uploader") or data.get("channel"),
            "duration": data.get("duration"),
            "thumbnail": data.get("thumbnail"),
            "heights": heights,
        })
    except Exception as e:  # noqa: BLE001
        send({"type": "info", "reqId": req, "error": str(e)})


def run_download(msg):
    job_id = msg["id"]
    exe = find_ytdlp()
    if not exe:
        send({"type": "error", "id": job_id, "message": "yt-dlp não encontrado. Rode host/install.sh."})
        return
    preset = PRESETS.get(msg.get("preset") or "best", PRESETS["best"])
    outdir = os.path.expanduser(msg.get("outdir") or "") or default_outdir()
    try:
        os.makedirs(outdir, exist_ok=True)
    except OSError as e:
        send({"type": "error", "id": job_id, "message": f"Não consegui criar a pasta {outdir}: {e}"})
        return

    args = base_args(exe) + preset + [
        "--newline", "--progress", "--progress-template", PROGRESS_TEMPLATE,
        "--print", "after_move:" + FILE_PREFIX + "%(filepath)s",
        "-P", outdir, "-o", "%(title)s [%(id)s].%(ext)s",
        "--", msg["url"],
    ]
    log("run:", " ".join(args))
    try:
        proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                encoding="utf-8", errors="replace", bufsize=1, env=child_env(),
                                start_new_session=True)
    except OSError as e:
        send({"type": "error", "id": job_id, "message": str(e)})
        return

    with _jobs_lock:
        _jobs[job_id] = proc
    send({"type": "started", "id": job_id, "outdir": outdir})

    stderr_lines = []

    def drain_stderr():
        for line in proc.stderr:
            stderr_lines.append(line.rstrip("\n"))
            del stderr_lines[:-50]

    t = threading.Thread(target=drain_stderr, daemon=True)
    t.start()

    filepath = None
    part = 0
    last_format = None
    last_sent = 0.0
    for line in proc.stdout:
        line = line.rstrip("\n")
        if line.startswith(PROGRESS_PREFIX):
            fields = line[len(PROGRESS_PREFIX):].split("\t")
            if len(fields) < 7:
                continue
            status, done, total, total_est, speed, eta, fmt = fields[:7]
            new_part = fmt != last_format
            if new_part:
                last_format = fmt
                part += 1
            total_n = num(total) or num(total_est)
            done_n = num(done)
            percent = (done_n / total_n * 100) if (done_n is not None and total_n) else None
            now = time.monotonic()
            if new_part or status == "finished" or now - last_sent >= 0.4:
                last_sent = now
                send({"type": "progress", "id": job_id, "part": part,
                      "status": "processing" if status == "finished" else "downloading",
                      "percent": round(percent, 1) if percent is not None else None,
                      "speed": num(speed), "eta": num(eta), "total": total_n})
        elif line.startswith(FILE_PREFIX):
            filepath = line[len(FILE_PREFIX):]
        elif line.strip():
            log("stdout:", line)

    code = proc.wait()
    t.join(timeout=2)
    with _jobs_lock:
        cancelled = getattr(proc, "_cancelled", False)
        _jobs.pop(job_id, None)

    if cancelled:
        send({"type": "cancelled", "id": job_id})
    elif code == 0:
        send({"type": "done", "id": job_id, "file": filepath, "outdir": outdir})
    else:
        log("stderr:", "\n".join(stderr_lines))
        send({"type": "error", "id": job_id, "message": last_error(stderr_lines)})


def cmd_download(msg):
    threading.Thread(target=run_download, args=(msg,), daemon=False).start()


def cmd_cancel(msg):
    with _jobs_lock:
        proc = _jobs.get(msg.get("id"))
        if proc and proc.poll() is None:
            proc._cancelled = True
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except OSError:
                proc.terminate()


def cmd_open(msg):
    path = os.path.expanduser(msg.get("path") or "") or default_outdir()
    target = path if os.path.isdir(path) else os.path.dirname(path)
    if not os.path.isdir(target):
        return
    try:
        subprocess.Popen(["xdg-open", target], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    except OSError as e:
        log("open failed:", e)


def cmd_update(msg):
    req = msg.get("reqId")
    exe = find_ytdlp()
    if not exe or not exe.startswith(LOCAL_BIN):
        send({"type": "update", "reqId": req,
              "error": "Só é possível atualizar o yt-dlp instalado pelo install.sh."})
        return
    out = subprocess.run([exe, "-U"], capture_output=True, text=True, timeout=300, env=child_env())
    _version_cache.pop(exe, None)
    send({"type": "update", "reqId": req, "ok": out.returncode == 0,
          "output": (out.stdout + out.stderr).strip()[-500:], "version": ytdlp_version(exe)})


COMMANDS = {
    "ping": cmd_ping,
    "info": lambda m: threading.Thread(target=cmd_info, args=(m,), daemon=True).start(),
    "download": cmd_download,
    "cancel": cmd_cancel,
    "open": cmd_open,
    "update": lambda m: threading.Thread(target=cmd_update, args=(m,), daemon=True).start(),
}


def main():
    log("host started, pid", os.getpid())
    while True:
        try:
            msg = read_message()
        except Exception as e:  # noqa: BLE001
            log("bad message:", e)
            continue
        if msg is None:
            break  # browser closed the port; running downloads still finish
        handler = COMMANDS.get(msg.get("cmd"))
        if handler:
            try:
                handler(msg)
            except Exception as e:  # noqa: BLE001
                log("handler error:", e)
                send({"type": "error", "id": msg.get("id"), "reqId": msg.get("reqId"), "message": str(e)})
    log("stdin closed, waiting for downloads")


if __name__ == "__main__":
    main()
