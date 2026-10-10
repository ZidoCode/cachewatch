#!/usr/bin/env python3
"""
cachewatch — cache-hit observability proxy for OpenAI-compatible gateways.

Sits in front of 9router (or any OpenAI-compatible endpoint), transparently
forwards /v1/* requests, and records token usage — especially cached prompt
tokens — into SQLite so you can actually see how much prompt caching is
saving you, per model, per day.

Zero external deps (stdlib only).
"""
import json
import os
import sqlite3
import threading
import time
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

UPSTREAM = os.environ.get("CW_UPSTREAM", "http://localhost:20128")
LISTEN_HOST = os.environ.get("CW_HOST", "127.0.0.1")
LISTEN_PORT = int(os.environ.get("CW_PORT", "20130"))
DB_PATH = os.environ.get("CW_DB", os.path.expanduser("~/.cachewatch/cachewatch.db"))

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

_db_lock = threading.Lock()


def db():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                model TEXT,
                endpoint TEXT,
                status INTEGER,
                prompt_tokens INTEGER DEFAULT 0,
                cached_tokens INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                latency_ms INTEGER DEFAULT 0,
                stream INTEGER DEFAULT 0,
                raw_usage TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_usage_ts ON usage(ts);
            CREATE INDEX IF NOT EXISTS idx_usage_model ON usage(model);
        """)
        # fix 2026-10-10: migration for existing installs
        try:
            conn.execute("ALTER TABLE usage ADD COLUMN cache_write_tokens INTEGER DEFAULT 0")
        except Exception:
            pass  # column already exists


def record(row):
    # fix 2026-10-10: optional 12th element = cache_write_tokens (Anthropic 1.25x billing)
    cw = row[11] if len(row) > 11 else 0
    with _db_lock:
        with db() as conn:
            conn.execute(
                """INSERT INTO usage
                   (ts, model, endpoint, status, prompt_tokens, cached_tokens,
                    completion_tokens, total_tokens, latency_ms, stream, raw_usage, cache_write_tokens)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                tuple(row[:11]) + (cw,),
            )


def extract_usage(payload):
    """Return (model, usage_dict) from a response body (json or SSE bytes/str)."""
    try:
        obj = json.loads(payload)
    except Exception:
        obj = None
    if not isinstance(obj, dict):
        # try raw_decode first (JSON with trailing junk / SSE tail)
        try:
            if isinstance(payload, bytes):
                payload = payload.decode("utf-8", "replace")
            obj, _ = json.JSONDecoder().raw_decode(str(payload).lstrip())
        except Exception:
            obj = None
    if not isinstance(obj, dict):
        # upstream may return SSE even for non-stream requests — parse data: lines
        model, usage, found = None, None, False
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8", "replace")
        for line in str(payload).splitlines():
            line = line.strip()
            if not line.startswith("data:"):
                continue
            pl = line[5:].strip()
            if pl == "[DONE]":
                continue
            try:
                o = json.loads(pl)
            except Exception:
                continue
            if isinstance(o, dict):
                found = True
                if o.get("model"):
                    model = o["model"]
                if o.get("usage"):
                    usage = o["usage"]
        return (model, usage) if found else (None, None)
    model = obj.get("model")
    usage = obj.get("usage")
    if usage is None:
        return model, None
    return model, usage


def norm_usage(usage):
    if not usage:
        return 0, 0, 0, 0
    prompt = usage.get("prompt_tokens") or usage.get("input_tokens") or 0
    completion = usage.get("completion_tokens") or usage.get("output_tokens") or 0
    total = usage.get("total_tokens") or (prompt + completion)
    cached = 0
    # OpenAI-style
    ptd = usage.get("prompt_tokens_details") or {}
    if isinstance(ptd, dict):
        cached = ptd.get("cached_tokens") or 0
    # Anthropic-style
    cached = cached or usage.get("cache_read_input_tokens") or 0
    # DeepSeek-style
    cached = cached or usage.get("prompt_cache_hit_tokens") or 0
    return prompt, cached, completion, total


def cache_write_tokens(usage):
    """Anthropic cache_creation_input_tokens (billed 1.25x) — fix 2026-10-10."""
    if not usage:
        return 0
    return usage.get("cache_creation_input_tokens") or 0



DASH_PREFIXES = ("/dashboard", "/login", "/callback", "/api/", "/_next/",
                 "/manifest.webmanifest")
DASH_FILES = ("/favicon.ico", "/favicon.svg")


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "cachewatch/0.1"

    def log_message(self, *a):
        pass  # quiet

    def _dash_path(self):
        return (self.path.startswith(DASH_PREFIXES)
                or self.path in DASH_FILES)

    def _api_path(self):
        return (self.path.startswith("/v1") or self._dash_path())

    def _forward(self, method):
        # dashboard/9r passthrough: proxy AS-IS to 9router (no usage recording,
        # no /v1-specific handling) — gives the full 9router UI (stations,
        # providers, keys, settings) under /dashboard/9r/
        if self.path.startswith("/login") or self.path.startswith("/callback"):
            # login pages live at root; inside /dashboard/9r they must map back there
            self.send_response(307)
            self.send_header("location", "/dashboard/9r" + self.path)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if self._dash_path():
            # strip the /dashboard/9r prefix; everything else passes as-is
            up_path = self.path
            if up_path == "/dashboard/9r" or up_path == "/dashboard/9r/":
                up_path = "/dashboard"
            elif up_path.startswith("/dashboard/9r/login") or up_path.startswith("/dashboard/9r/callback"):
                up_path = up_path[len("/dashboard/9r"):]  # login lives at root
            elif up_path.startswith("/dashboard/9r/"):
                up_path = "/dashboard/" + up_path[len("/dashboard/9r/"):]
            # plain /dashboard or /dashboard/* already correct — pass as-is
            url = UPSTREAM.rstrip("/") + up_path
            try:
                length = int(self.headers.get("Content-Length", 0) or 0)
                req_body = self.rfile.read(length) if length else None
                headers = {k: v for k, v in self.headers.items() if k.lower() not in ("host", "connection")}
                req = Request(url, data=req_body, headers=headers, method=method)
                # do NOT follow redirects — pass 307/location straight to client
                import urllib.request as _ur
                class _NoRedir(_ur.HTTPRedirectHandler):
                    def redirect_request(self, req, fp, code, msg, headers, newurl):
                        # forward the 3xx to the client instead of raising TypeError
                        raise _ur.HTTPError(req.full_url, code, msg, headers, fp)
                opener = _ur.build_opener(_NoRedir)
                try:
                    resp = opener.open(req, timeout=60)
                    data = resp.read()
                except _ur.HTTPError as e:
                    resp = e
                    data = e.read()
                self.send_response(resp.status)
                for k, v in resp.headers.items():
                    # keep content-encoding: body is forwarded byte-identical
                    if k.lower() not in ("transfer-encoding", "connection", "content-length"):
                        self.send_header(k, v)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except Exception:
                body = b'{"error":{"message":"upstream error"}}'
                self.send_response(502)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            return

        length = int(self.headers.get("Content-Length", 0) or 0)
        body = self.rfile.read(length) if length else None

        # peek at model + stream from request body
        model = None
        stream = 0
        if body:
            try:
                req_obj = json.loads(body)
                model = req_obj.get("model")
                stream = 1 if req_obj.get("stream") else 0
                # fix 2026-10-10: ask upstream for usage in the final SSE chunk so
                # streamed requests get recorded instead of 0/0 (biased hit-rate)
                if stream and "chat/completions" in (self.path or ""):
                    so = req_obj.get("stream_options") or {}
                    if isinstance(so, dict) and not so.get("include_usage"):
                        so["include_usage"] = True
                        req_obj["stream_options"] = so
                        body = json.dumps(req_obj).encode()
            except Exception:
                pass

        path = self.path
        endpoint = path.split("?")[0]
        url = UPSTREAM.rstrip("/") + path
        headers = {k: v for k, v in self.headers.items()
                   if k.lower() not in ("host", "content-length", "connection")}
        headers["X-Cachewatch-Client"] = "1"

        start = time.time()
        status = 0
        try:
            req = Request(url, data=body, headers=headers, method=method)
            resp = urlopen(req, timeout=600)
            status = resp.status
            hdrs = [(k, v) for k, v in resp.headers.items()
                    if k.lower() not in ("transfer-encoding", "connection", "content-length")]
            if stream:
                # stream: forward chunked, tee bytes to recover usage
                self.send_response(status)
                for k, v in hdrs:
                    self.send_header(k, v)
                self.send_header("Transfer-Encoding", "chunked")
                self.end_headers()
                from collections import deque
                accum = deque(maxlen=256)  # cap RAM: only last ~256 chunks needed (usage is in the final chunk)
                while True:
                    chunk = resp.readline()
                    if not chunk:
                        break
                    accum.append(chunk)
                    try:
                        self.wfile.write(("%x\r\n" % len(chunk)).encode())
                        self.wfile.write(chunk)
                        self.wfile.write(b"\r\n")
                    except (BrokenPipeError, ConnectionResetError):
                        break
                try:
                    self.wfile.write(b"0\r\n\r\n")
                except Exception:
                    pass
                joined = b"".join(accum)
                model2, usage = self._usage_from_stream(joined)
                model = model2 or model
                if usage:
                    p, c, comp, t = norm_usage(usage)
                    record((self._now(), model, endpoint, status, p, c, comp, t,
                            int((time.time() - start) * 1000), stream,
                            json.dumps(usage), cache_write_tokens(usage)))
            else:
                # non-stream: read fully, then send accurate Content-Length
                data = resp.read()
                self.send_response(status)
                for k, v in hdrs:
                    self.send_header(k, v)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                try:
                    self.wfile.write(data)
                except Exception:
                    pass
                m2, usage = extract_usage(data)
                model = m2 or model
                if usage:
                    p, c, comp, t = norm_usage(usage)
                    record((self._now(), model, endpoint, status, p, c, comp, t,
                            int((time.time() - start) * 1000), stream,
                            json.dumps(usage), cache_write_tokens(usage)))
                else:
                    record((self._now(), model, endpoint, status, 0, 0, 0, 0,
                            int((time.time() - start) * 1000), stream, None))
        except HTTPError as e:
            status = e.code
            data = e.read()
            self.send_response(status)
            for k, v in e.headers.items():
                if k.lower() in ("transfer-encoding", "connection", "content-length"):
                    continue
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            try:
                self.wfile.write(data)
            except Exception:
                pass
            m2, usage = extract_usage(data)
            if m2:
                model = m2
            record((self._now(), model, endpoint, status, 0, 0, 0, 0,
                    int((time.time() - start) * 1000), stream, None))
        except URLError as e:
            msg = json.dumps({"error": {"message": f"upstream unreachable: {e}"}}).encode()
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)

    @staticmethod
    def _usage_from_stream(chunk_bytes):
        model = None
        usage = None
        for line in chunk_bytes.split(b"\n"):
            line = line.strip()
            if not line.startswith(b"data:"):
                continue
            payload = line[5:].strip()
            if payload == b"[DONE]":
                continue
            try:
                obj = json.loads(payload)
            except Exception:
                continue
            if isinstance(obj, dict):
                if obj.get("model"):
                    model = obj["model"]
                if obj.get("usage"):
                    usage = obj["usage"]
        return model, usage

    @staticmethod
    def _now():
        return datetime.now(timezone.utc).isoformat()

    def do_POST(self):
        p = self.path
        if p.startswith("/cw/") or p == "/cw":
            self.path = "/_cw" + p[3:]
        if self.path.startswith("/_cw/"):
            return self._meta()
        if not self._api_path():
            body = b'{"error":{"message":"not found"}}'
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self._forward("POST")

    def do_GET(self):
        p = self.path
        if p.startswith("/cw/") or p == "/cw":
            self.path = "/_cw" + p[3:]  # defensive: handle unrewritten public prefix
        if self.path.startswith("/_cw/"):
            return self._meta()
        # only proxy API traffic + the full 9router dashboard under /dashboard/9r;
        # other browser paths must NOT leak to the 9router dashboard
        if not self._api_path():
            body = b'{"error":{"message":"not found"}}'
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Clear-Site-Data", '"cache", "storage", "cookies"')
            self.end_headers()
            self.wfile.write(body)
            return
        self._forward("GET")

    def _meta(self):
        # tiny built-in stats endpoint
        if self.path.startswith("/_cw/stats"):
            with db() as conn:
                rows = conn.execute(
                    """SELECT model,
                              SUM(prompt_tokens) p, SUM(cached_tokens) c,
                              SUM(completion_tokens) o, COUNT(*) n
                       FROM usage GROUP BY model ORDER BY p DESC"""
                ).fetchall()
            out = []
            for r in rows:
                p, c = r["p"] or 0, r["c"] or 0
                out.append({
                    "model": r["model"], "requests": r["n"],
                    "prompt_tokens": p, "cached_tokens": c,
                    "completion_tokens": r["o"] or 0,
                    "cache_hit_pct": round(100.0 * c / p, 2) if p else 0.0,
                })
            body = json.dumps({"models": out}, indent=2).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path.startswith("/_cw/data/"):
            import data9r
            name = self.path.split("/_cw/data/")[1].split("?")[0].rstrip("/")
            try:
                if name == "summary":
                    s = data9r.summary()
                    if not s["requests"]:
                        y = data9r.usage_days(2)
                        if y and y[-1]["date"] != s["date"]:
                            s = {**y[-1], "date": y[-1]["date"], "ok_pct": None, "note": "kemarin"}
                    body = json.dumps(s).encode()
                elif name == "hourly":
                    body = json.dumps({"hours": data9r.hourly()}).encode()
                elif name == "providers":
                    body = json.dumps({"providers": data9r.providers()}).encode()
                elif name == "keys":
                    body = json.dumps({"keys": data9r.keys()}).encode()
                elif name == "models":
                    body = json.dumps({"models": data9r.models_today()}).encode()
                elif name == "logs":
                    body = json.dumps({"logs": data9r.recent_logs(40)}).encode()
                elif name == "cw":
                    body = json.dumps({"cw": data9r.cw_stats()}).encode()
                elif name == "days":
                    body = json.dumps({"days": data9r.usage_days(7)}).encode()
                elif name == "all":
                    s = data9r.summary()
                    if not s["requests"]:
                        y = data9r.usage_days(2)
                        if y and y[-1]["date"] != s["date"]:
                            s = {**y[-1], "ok_pct": None, "note": "kemarin"}
                    import subprocess as _sp2
                    hv = {}
                    for _s in ["router", "cachewatch", "ttyd", "ngrok", "9router"]:
                        try:
                            hv[_s] = _sp2.run(["systemctl", "is-active", _s], capture_output=True, text=True, timeout=5).stdout.strip()
                        except Exception:
                            hv[_s] = "unknown"
                    # security fix 2026-10-10: never serialize API keys, providers trimmed to name/status only
                    provs = [{"name": p.get("name"), "ok": p.get("ok", p.get("active"))}
                             for p in (data9r.providers() or [])]
                    body = json.dumps({
                        "summary": s,
                        "hourly": data9r.hourly(),
                        "providers": provs,
                        "keys": [{"name": k["name"], "created": k["created"], "key": "(hidden)"} for k in data9r.keys()],
                        "models": data9r.models_today(),
                        "logs": data9r.recent_logs(40),
                        "cw": data9r.cw_stats(),
                        "days": data9r.usage_days(7),
                        "health": hv,
                    }).encode()
                elif name == "opsdata":
                    # sanitized feed for the public ops dashboard (no keys, no emails)
                    s = data9r.summary()
                    if not s["requests"]:
                        y = data9r.usage_days(2)
                        if y and y[-1]["date"] != s["date"]:
                            s = {**y[-1], "ok_pct": None, "note": "kemarin"}
                    import subprocess as _sp3
                    hv = {}
                    for _s in ["router", "cachewatch", "ttyd", "ngrok", "9router"]:
                        try:
                            hv[_s] = _sp3.run(["systemctl", "is-active", _s], capture_output=True, text=True, timeout=5).stdout.strip()
                        except Exception:
                            hv[_s] = "unknown"
                    provs = [{"name": p.get("name"), "ok": p.get("ok", p.get("active"))}
                             for p in (data9r.providers() or [])]
                    body = json.dumps({
                        "summary": s,
                        "hourly": data9r.hourly(),
                        "providers": provs,
                        "keys": [{"name": k["name"], "created": k["created"], "key": "(hidden)"} for k in data9r.keys()],
                        "models": data9r.models_today(),
                        "logs": data9r.recent_logs(40),
                        "cw": data9r.cw_stats(),
                        "days": data9r.usage_days(7),
                        "health": hv,
                    }).encode()
                else:
                    body = b'{"error":"unknown data endpoint"}'
                    self.send_response(404)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except Exception as e:
                body = json.dumps({"error": str(e)}).encode()
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            return
        if self.path.startswith("/_cw/health"):
            import subprocess as _sp
            svcs = ["router", "cachewatch", "ttyd", "ngrok", "9router"]
            out = {}
            for s in svcs:
                try:
                    r = _sp.run(["systemctl", "is-active", s], capture_output=True, text=True, timeout=5)
                    out[s] = r.stdout.strip()
                except Exception:
                    out[s] = "unknown"
            body = json.dumps(out).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path.startswith("/_cw/ops") or self.path.startswith("/_cw/home") or self.path.startswith("/_cw/v2") or self.path.startswith("/_cw/map"):
            import ops_v3
            body = ops_v3.OPS_V3.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
            self.send_header("Clear-Site-Data", '"cache", "storage"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path.startswith("/_cw/dashboard") or self.path.startswith("/_cw/panel") or self.path.startswith("/_cw/live"):
            body = self._dashboard_html().encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
            self.send_header("Clear-Site-Data", '"cache", "storage"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path.startswith("/_cw/daily"):
            with db() as conn:
                rows = conn.execute(
                    """SELECT substr(ts,1,10) d, model,
                              SUM(prompt_tokens) p, SUM(cached_tokens) c,
                              SUM(completion_tokens) o, COUNT(*) n
                       FROM usage GROUP BY d, model ORDER BY d DESC"""
                ).fetchall()
            out = []
            for r in rows:
                p, c = r["p"] or 0, r["c"] or 0
                out.append({
                    "date": r["d"], "model": r["model"], "requests": r["n"],
                    "prompt_tokens": p, "cached_tokens": c,
                    "completion_tokens": r["o"] or 0,
                    "cache_hit_pct": round(100.0 * c / p, 2) if p else 0.0,
                })
            body = json.dumps({"daily": out}, indent=2).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        body = b'{"ok":true,"service":"cachewatch"}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    @staticmethod
    def _ops_html():
        return """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>ops · vps</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>⚡</text></svg>">
<style>
:root{color-scheme:dark;--bg:#05070c;--p1:rgba(255,255,255,.045);--p2:rgba(255,255,255,.07);--line:rgba(255,255,255,.09);--txt:#e8eefb;--dim:#64748f;--a:#6d8bff;--a2:#b06cff;--ok:#34e28a;--warn:#f0b64a;--bad:#ff5c66}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html,body{margin:0;min-height:100%}
body{background:var(--bg);color:var(--txt);font:14px/1.5 ui-sans-serif,-apple-system,'Segoe UI',Roboto,sans-serif;display:flex;flex-direction:column;min-height:100vh;background-image:radial-gradient(900px 500px at 85% -5%,rgba(109,139,255,.14),transparent 60%),radial-gradient(700px 400px at -10% 110%,rgba(176,108,255,.10),transparent 60%)}
.bggrid{position:fixed;inset:0;background-image:linear-gradient(rgba(255,255,255,.025) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.025) 1px,transparent 1px);background-size:44px 44px;pointer-events:none;mask-image:radial-gradient(70% 60% at 50% 30%,#000 30%,transparent 100%)}
header{display:flex;align-items:center;gap:11px;padding:16px 18px 10px}
.glow{position:relative;width:38px;height:38px;flex:none}
.glow::before{content:'';position:absolute;inset:-6px;border-radius:14px;background:conic-gradient(from 210deg,var(--a),var(--a2),#34e28a,var(--a));filter:blur(12px);opacity:.5}
.logo{position:absolute;inset:0;border-radius:12px;background:linear-gradient(135deg,var(--a),var(--a2));display:grid;place-items:center;font-size:18px;box-shadow:inset 0 1px 0 rgba(255,255,255,.35)}
header h1{margin:0;font-size:16px;font-weight:800;letter-spacing:.3px}
header .sub{color:var(--dim);font-size:11px;margin-top:1px}
.tabs{margin-left:auto;display:flex;background:var(--p1);border:1px solid var(--line);border-radius:11px;padding:3px;gap:2px}
.tab{padding:7px 14px;border-radius:8px;color:var(--dim);font-size:12.5px;font-weight:600;cursor:pointer;border:none;background:transparent;transition:.18s}
.tab.on{background:linear-gradient(135deg,rgba(109,139,255,.22),rgba(176,108,255,.22));color:#fff;box-shadow:inset 0 0 0 1px rgba(109,139,255,.35)}
main{flex:1;min-height:0;display:none;flex-direction:column;overflow:hidden;padding:0 14px}
main.on{display:flex}
.kpis{display:grid;grid-template-columns:repeat(2,1fr);gap:9px;padding:6px 0 10px}
.kpi{position:relative;overflow:hidden;background:var(--p1);border:1px solid var(--line);border-radius:16px;padding:12px 13px;backdrop-filter:blur(10px)}
.kpi::after{content:'';position:absolute;top:0;left:12%;right:12%;height:1px;background:linear-gradient(90deg,transparent,rgba(255,255,255,.28),transparent)}
.kpi .l{font-size:9.5px;text-transform:uppercase;letter-spacing:1.1px;color:var(--dim);font-weight:600}
.kpi .v{font-size:22px;font-weight:800;margin-top:3px;font-variant-numeric:tabular-nums}
.kpi .t{font-size:10px;color:var(--dim);margin-top:1px}
.svc{display:flex;flex-wrap:wrap;gap:6px;padding:2px 0 10px}
.pill{display:inline-flex;align-items:center;gap:6px;font-size:11px;padding:5px 11px;border-radius:999px;background:var(--p1);border:1px solid var(--line);color:var(--dim);font-weight:600}
.dot{width:7px;height:7px;border-radius:50%;background:var(--dim)}
.dot.up{background:var(--ok);box-shadow:0 0 10px var(--ok);animation:pulse 2.4s infinite}
@keyframes pulse{50%{opacity:.55}}
.dot.down{background:var(--bad);box-shadow:0 0 10px var(--bad)}
.panel{background:var(--p1);border:1px solid var(--line);border-radius:16px;overflow:hidden;backdrop-filter:blur(10px)}
.panel .ph{display:flex;align-items:center;justify-content:space-between;padding:11px 14px;border-bottom:1px solid var(--line);font-size:12px;font-weight:700;color:#c9d4ea}
.panel .ph span{color:var(--dim);font-weight:500;font-size:10.5px}
.rows{max-height:42vh;overflow:auto}
table{width:100%;border-collapse:collapse}
th{position:sticky;top:0;background:rgba(10,14,22,.92);backdrop-filter:blur(6px);color:var(--dim);font-size:9.5px;text-transform:uppercase;letter-spacing:.8px;text-align:left;padding:9px 14px;border-bottom:1px solid var(--line)}
td{padding:10px 14px;border-bottom:1px solid rgba(255,255,255,.05);font-size:12.5px;font-variant-numeric:tabular-nums}
tr:last-child td{border-bottom:none}
.mname{font-weight:600;color:#cfdaf0}
.mnull{color:var(--dim);font-style:italic}
.bar{height:6px;border-radius:4px;background:rgba(255,255,255,.06);overflow:hidden;margin-top:5px}
.bar>i{display:block;height:100%;border-radius:4px;background:linear-gradient(90deg,var(--a),var(--a2))}
.hi{color:var(--ok);font-weight:700}.hw{color:var(--warn);font-weight:700}.hb{color:var(--bad);font-weight:700}
.spark{display:flex;align-items:flex-end;gap:2px;height:34px;margin:8px 14px 12px}
.spark i{flex:1;min-width:3px;border-radius:2px 2px 0 0;background:linear-gradient(180deg,var(--a),rgba(109,139,255,.15));min-height:2px}
.termwrap{flex:1;min-height:0;display:flex;padding-bottom:12px}
.termwrap iframe{flex:1;border:1px solid var(--line);border-radius:16px;background:#000;width:100%;height:100%}
.foot{padding:10px 18px 14px;color:var(--dim);font-size:10.5px;display:flex;justify-content:space-between;align-items:center}
.foot .live{display:inline-flex;align-items:center;gap:6px}
.foot .live::before{content:'';width:6px;height:6px;border-radius:50%;background:var(--ok);box-shadow:0 0 8px var(--ok);animation:pulse 2.4s infinite}
.empty{padding:26px;text-align:center;color:var(--dim);font-size:12.5px}
</style></head><body>
<div class="bggrid"></div>
<header>
  <div class="glow"><div class="logo">⚡</div></div>
  <div><h1>ops hub</h1><div class="sub">VPS · 161.120.174.237</div></div>
  <div class="tabs">
    <button class="tab on" id="tStats" onclick="show('stats')">Stats</button>
    <button class="tab" id="tTerm" onclick="show('term')">Terminal</button>
  </div>
</header>

<main id="mStats" class="on">
  <div class="kpis" id="kpis"></div>
  <div class="svc" id="svc"></div>
  <div class="panel">
    <div class="ph">Cache hit per model <span id="upd">—</span></div>
    <div class="rows">
      <table><thead><tr><th>Model</th><th>Req</th><th>Prompt</th><th>Cached</th><th>Hit</th></tr></thead>
      <tbody id="rows"><tr><td colspan="5" class="empty">loading…</td></tr></tbody></table>
    </div>
    <div class="spark" id="spark"></div>
  </div>
</main>

<main id="mTerm">
  <div class="termwrap"><iframe src="/term/" title="terminal"></iframe></div>
</main>

<div class="foot"><span class="live">live</span><span>cachewatch · ttyd · single origin</span></div>
<script>
const ABS=new URL(location.href);ABS.pathname=ABS.pathname.replace(/\\/(ops|home|panel|dashboard|live)\\/?$/,'/');
async function jget(u){
  for(let i=0;i<3;i++){
    try{
      const r=await fetch(ABS+u,{cache:'no-store',headers:{'ngrok-skip-browser-warning':'1'}});
      const t=await r.text();
      if(t.trim().startsWith('{'))return JSON.parse(t);
    }catch(e){}
    await new Promise(r=>setTimeout(r,700));
  }
  throw new Error('bad json');
}
function cls(p){return p>=60?'hi':p>=20?'hw':'hb'}
function show(w){
  document.getElementById('mStats').classList.toggle('on',w==='stats');
  document.getElementById('mTerm').classList.toggle('on',w==='term');
  document.getElementById('tStats').classList.toggle('on',w==='stats');
  document.getElementById('tTerm').classList.toggle('on',w==='term');
}
function card(l,v,c,t){return '<div class="kpi"><div class="l">'+l+'</div><div class="v '+c+'">'+v+'</div><div class="t">'+(t||'&nbsp;')+'</div></div>'}
const hist=[];
async function tick(){
  try{
    const j=await jget('stats');
    let tp=0,tc=0,tr=0;
    (j.models||[]).forEach(m=>{tp+=m.prompt_tokens;tc+=m.cached_tokens;tr+=m.requests});
    const pct=tp?100*tc/tp:0;
    hist.push(tr);if(hist.length>40)hist.shift();
    document.getElementById('kpis').innerHTML=
      card('Requests',tr,'','total requests')+
      card('Hit rate',pct.toFixed(1)+'%',cls(pct),'cached ÷ prompt')+
      card('Prompt tokens',fmt(tp),'')+
      card('Cached tokens',fmt(tc),'','billed cheaper');
    document.getElementById('rows').innerHTML=(j.models||[]).filter(m=>m.prompt_tokens>0).map(m=>
      '<tr><td class="'+(m.model?'mname':'mnull')+'">'+(m.model||'unknown')+'</td><td>'+m.requests+'</td><td>'+fmt(m.prompt_tokens)+'</td><td>'+fmt(m.cached_tokens)+'</td>'+
      '<td><span class="'+cls(m.cache_hit_pct)+'">'+m.cache_hit_pct.toFixed(1)+'%</span><div class="bar"><i style="width:'+Math.min(100,m.cache_hit_pct)+'%"></i></div></td></tr>'
    ).join('')||'<tr><td colspan="5" class="empty">no traffic yet</td></tr>';
    const mx=Math.max(...hist,1);
    document.getElementById('spark').innerHTML=hist.map(v=>'<i style="height:'+Math.max(8,100*v/mx)+'%"></i>').join('');
    document.getElementById('upd').textContent='updated '+new Date().toLocaleTimeString();
  }catch(e){document.getElementById('upd').textContent='retrying…'}
  try{
    const j=await jget('health');
    document.getElementById('svc').innerHTML=Object.entries(j).map(([k,v])=>
      '<span class="pill"><span class="dot '+(v==='active'?'up':'down')+'"></span>'+k+'</span>').join('');
  }catch(e){}
}
function fmt(n){return n>=1e6?(n/1e6).toFixed(1)+'M':n>=1e3?(n/1e3).toFixed(1)+'k':String(n)}
tick();setInterval(tick,5000);
</script></body></html>"""

    @staticmethod
    def _dashboard_html():
        return """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>cachewatch</title>
<style>
:root{color-scheme:dark}
body{margin:0;background:#0b0f14;color:#e6edf3;font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;padding:20px}
h1{font-size:20px;margin:0 0 4px}
.sub{color:#8b949e;font-size:12px;margin-bottom:20px}
.cards{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:20px}
.card{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:14px 18px;min-width:130px}
.card .v{font-size:24px;font-weight:700}
.card .l{color:#8b949e;font-size:11px;text-transform:uppercase;letter-spacing:.5px}
.good{color:#3fb950}.warn{color:#d29922}.bad{color:#f85149}
table{width:100%;border-collapse:collapse;background:#161b22;border:1px solid #30363d;border-radius:10px;overflow:hidden}
th,td{text-align:left;padding:9px 12px;border-bottom:1px solid #21262d;font-size:13px}
th{background:#1c2128;color:#8b949e;font-weight:600;text-transform:uppercase;font-size:11px;letter-spacing:.5px}
tr:last-child td{border-bottom:none}
.bar{height:7px;border-radius:4px;background:#21262d;overflow:hidden;margin-top:5px}
.bar>i{display:block;height:100%;background:linear-gradient(90deg,#3fb950,#2ea043)}
</style></head><body>
<h1>⚡ cachewatch</h1>
<div class="sub">prompt-cache observability · fronting 9router · <span id="ts">loading…</span></div>
<div class="cards" id="cards"></div>
<h1 style="font-size:15px;margin:18px 0 10px">Per-model cache hit</h1>
<table><thead><tr><th>Model</th><th>Req</th><th>Prompt tok</th><th>Cached tok</th><th>Hit %</th></tr></thead>
<tbody id="rows"><tr><td colspan="5">loading…</td></tr></tbody></table>
<script>
function cls(p){return p>=60?'good':p>=20?'warn':'bad'}
async function tick(){
  try{
    const r=await fetch('stats');const j=await r.json();
    let tp=0,tc=0,tr=0;
    j.models.forEach(m=>{tp+=m.prompt_tokens;tc+=m.cached_tokens;tr+=m.requests});
    const pct=tp?100*tc/tp:0;
    document.getElementById('cards').innerHTML=
      '<div class="card"><div class="l">Requests</div><div class="v">'+tr+'</div></div>'+
      '<div class="card"><div class="l">Prompt tokens</div><div class="v">'+tp.toLocaleString()+'</div></div>'+
      '<div class="card"><div class="l">Cached tokens</div><div class="v">'+tc.toLocaleString()+'</div></div>'+
      '<div class="card"><div class="l">Overall hit</div><div class="v '+cls(pct)+'">'+pct.toFixed(1)+'%</div></div>';
    document.getElementById('rows').innerHTML=j.models.map(m=>
      '<tr><td>'+m.model+'</td><td>'+m.requests+'</td><td>'+m.prompt_tokens.toLocaleString()+'</td>'+
      '<td>'+m.cached_tokens.toLocaleString()+'</td>'+
      '<td><span class="'+cls(m.cache_hit_pct)+'">'+m.cache_hit_pct.toFixed(1)+'%</span>'+
      '<div class="bar"><i style="width:'+Math.min(100,m.cache_hit_pct)+'%"></i></div></td></tr>'
    ).join('')||'<tr><td colspan="5">no data yet</td></tr>';
    document.getElementById('ts').textContent='updated '+new Date().toLocaleTimeString();
  }catch(e){document.getElementById('ts').textContent='error: '+e}
}
tick();setInterval(tick,5000);
</script></body></html>"""


def main():
    init_db()
    srv = ThreadingHTTPServer((LISTEN_HOST, LISTEN_PORT), Handler)
    srv.daemon_threads = True
    print(f"cachewatch listening on {LISTEN_HOST}:{LISTEN_PORT} -> {UPSTREAM}")
    print(f"db: {DB_PATH}")
    srv.serve_forever()


if __name__ == "__main__":
    main()
