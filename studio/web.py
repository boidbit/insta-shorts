"""Tiny web page: type an idea or a script, press "Banao", get the reel.

    python -m studio.web                      # http://127.0.0.1:7860
    python -m studio.web --host 0.0.0.0       # on a server (Hugging Face Space, VPS...)

Only the Python standard library is used. Videos are rendered one at a time in a
background thread; the page polls the job for progress. Set STUDIO_PASSWORD to
require a password before anything is rendered.
"""
import argparse
import json
import os
import queue
import re
import threading
import time
import traceback
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import director, hooks, script
from .characters import LOOKS
from .render import make_video
from .util import ROOT, load_scene

OUT = os.path.join(ROOT, "out", "web")
PAGE = os.path.join(ROOT, "web", "index.html")
EXAMPLE_SCRIPT = os.path.join(ROOT, "scripts", "doodh_story.txt")
JOBS = {}
WORK = queue.Queue()
NAME_RE = re.compile(r"^[a-f0-9]{32}\.(mp4|json|txt|png)$")


def _job_view(job):
    return {k: v for k, v in job.items() if not k.startswith("_")}


def run_job(job):
    req = job["_req"]

    def log(msg):
        job["log"].append(str(msg).strip())

    try:
        mode, text = req.get("mode", "idea"), req.get("text", "")
        hook_style = req.get("hook") or "auto"
        style = req.get("style") if req.get("style") in ("2d", "2.5d") else None
        if mode == "json":
            scene = json.loads(text)
        elif mode == "script" and not (req.get("use_ai") and director.provider_name()):
            job["stage"] = "Script padh raha hoon"
            scene, warnings = script.parse_script(text)
            for w in warnings:
                log("⚠ " + w)
        else:
            job["stage"] = "AI kahani likh raha hai"
            scene = director.direct(text, hook_style, log=log, style=style or "2d")
        base = os.path.join(OUT, job["id"])
        director.save(scene, base + ".json")
        job["scene"] = scene
        job["post"] = director.post_text(scene)
        job["stage"] = "Video ban raha hai"
        video = make_video(load_scene(base + ".json"), int(req.get("width", 720)), use_tts=bool(req.get("voice", True)),
                           style=style)
        job["duration"] = video.duration
        video.frame(min(1.0, video.duration / 2)).resize((270, 480)).save(base + ".png")
        video.render_video(base + ".mp4", progress=lambda f: job.update(progress=round(f, 3)))
        job.update(status="done", stage="Ho gaya ✅", progress=1.0,
                   video="/files/%s.mp4" % job["id"], cover="/files/%s.png" % job["id"])
    except BaseException as e:  # SystemExit from director / ffmpeg too
        log(traceback.format_exc(limit=3))
        job.update(status="error", stage="Gadbad ho gayi", error=str(e) or e.__class__.__name__)


def worker():
    while True:
        job = WORK.get()
        job["status"] = "running"
        job["started"] = time.time()
        run_job(job)
        WORK.task_done()


class Handler(BaseHTTPRequestHandler):
    server_version = "DesiToons/1.0"

    def log_message(self, fmt, *args):
        if "/api/job" not in (args[0] if args else ""):
            super().log_message(fmt, *args)

    def _send(self, code, body, ctype="application/json; charset=utf-8", headers=None):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        elif isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self):
        pw = os.environ.get("STUDIO_PASSWORD")
        return not pw or self.headers.get("X-Studio-Password") == pw

    def do_GET(self):
        path, _, qs = self.path.partition("?")
        if path in ("/", "/index.html"):
            with open(PAGE, encoding="utf-8") as f:
                return self._send(200, f.read(), "text/html; charset=utf-8")
        if path == "/api/info":
            example = ""
            if os.path.isfile(EXAMPLE_SCRIPT):
                with open(EXAMPLE_SCRIPT, encoding="utf-8") as f:
                    example = f.read()
            return self._send(200, {
                "provider": director.provider_name(),
                "password": bool(os.environ.get("STUDIO_PASSWORD")),
                "hooks": [{"key": k, "name": h["name"]} for k, h in hooks.HOOKS.items()],
                "looks": list(LOOKS),
                "example_script": example,
            })
        if path == "/api/job":
            jid = dict(p.split("=", 1) for p in qs.split("&") if "=" in p).get("id", "")
            job = JOBS.get(jid)
            if not job:
                return self._send(404, {"error": "job not found"})
            view = _job_view(job)
            if job["status"] == "queued":
                view["queue"] = sum(1 for j in JOBS.values() if j["status"] == "queued" and j["created"] <= job["created"])
            return self._send(200, view)
        if path.startswith("/files/"):
            return self._file(path[len("/files/"):])
        self._send(404, {"error": "not found"})

    def _file(self, name):
        if not NAME_RE.match(name) or not os.path.isfile(os.path.join(OUT, name)):
            return self._send(404, {"error": "not found"})
        full = os.path.join(OUT, name)
        size = os.path.getsize(full)
        ctype = {"mp4": "video/mp4", "json": "application/json", "txt": "text/plain; charset=utf-8",
                 "png": "image/png"}[name.rsplit(".", 1)[1]]
        start, end, code = 0, size - 1, 200
        m = re.match(r"bytes=(\d*)-(\d*)", self.headers.get("Range", ""))
        if m and (m.group(1) or m.group(2)):
            if m.group(1):
                start = int(m.group(1))
                end = int(m.group(2)) if m.group(2) else end
            else:
                start = max(0, size - int(m.group(2)))
            end = min(end, size - 1)
            code = 206
        with open(full, "rb") as f:
            f.seek(start)
            data = f.read(end - start + 1)
        headers = {"Accept-Ranges": "bytes"}
        if code == 206:
            headers["Content-Range"] = "bytes %d-%d/%d" % (start, end, size)
        if "download=1" in self.path:
            headers["Content-Disposition"] = 'attachment; filename="desi_toons_%s"' % name
        self._send(code, data, ctype, headers)

    def do_POST(self):
        if self.path != "/api/make":
            return self._send(404, {"error": "not found"})
        if not self._authorized():
            return self._send(HTTPStatus.UNAUTHORIZED, {"error": "password galat hai"})
        try:
            n = int(self.headers.get("Content-Length", "0"))
            req = json.loads(self.rfile.read(min(n, 200000)).decode("utf-8") or "{}")
        except ValueError:
            return self._send(400, {"error": "bad request"})
        mode = req.get("mode", "idea")
        if mode not in ("idea", "script", "json"):
            return self._send(400, {"error": "unknown mode"})
        if mode == "idea" and not director.provider_name():
            return self._send(400, {"error": "Idea mode ke liye AI key chahiye (GEMINI_API_KEY free hai). "
                                             "Tab tak 'Apni script' use karo."})
        if mode != "idea" and not req.get("text", "").strip():
            return self._send(400, {"error": "Kuch likho to sahi 🙂"})
        job = dict(id=uuid.uuid4().hex, status="queued", stage="Line me hai", progress=0.0, log=[],
                   created=time.time(), mode=mode, _req=req)
        JOBS[job["id"]] = job
        WORK.put(job)
        self._send(200, {"id": job["id"]})


def main(argv=None):
    ap = argparse.ArgumentParser(description="Desi Toons Studio web page")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=int(os.environ.get("PORT", 7860)))
    args = ap.parse_args(argv)
    os.makedirs(OUT, exist_ok=True)
    threading.Thread(target=worker, daemon=True).start()
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print("Desi Toons Studio: http://%s:%d  (AI: %s)" % (args.host, args.port, director.provider_name() or "off"))
    srv.serve_forever()


if __name__ == "__main__":
    main()
