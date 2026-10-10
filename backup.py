#!/usr/bin/env python3
"""Backup 9router + cachewatch ke Telegram (dokumen) — lari via cron.
Ambil kredensial dari ~/.hermes/.env (TELEGRAM_BOT_TOKEN, chat id di arg)."""
import os, sys, json, time, tarfile, io, urllib.request, urllib.parse, hashlib

HOME = os.path.expanduser("~")
TOKEN = None
for line in open(f"{HOME}/.hermes/.env"):
    line = line.strip()
    if line.startswith("TELEGRAM_BOT_TOKEN="):
        TOKEN = line.split("=", 1)[1].strip().strip('"').strip("'")
if not TOKEN:
    sys.exit("no token")

CHAT = sys.argv[1] if len(sys.argv) > 1 else "6905566220"

def send_file(path, caption):
    url = f"https://api.telegram.org/bot{TOKEN}/sendDocument"
    boundary = "----bw" + hashlib.md5(str(time.time()).encode()).hexdigest()
    fname = os.path.basename(path)
    with open(path, "rb") as f:
        data = f.read()
    body = io.BytesIO()
    def part(name, val):
        body.write(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{val}\r\n".encode())
    part("chat_id", CHAT)
    part("caption", caption)
    body.write(f"--{boundary}\r\nContent-Disposition: form-data; name=\"document\"; filename=\"{fname}\"\r\nContent-Type: application/gzip\r\n\r\n".encode())
    body.write(data)
    body.write(f"\r\n--{boundary}--\r\n".encode())
    req = urllib.request.Request(url, data=body.getvalue(),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    try:
        r = urllib.request.urlopen(req, timeout=120)
        return r.status == 200
    except Exception as e:
        print("send fail:", e)
        return False

STAMP = time.strftime("%Y%m%d")
OUT = f"/tmp/9router-backup-{STAMP}.tar.gz"
with tarfile.open(OUT, "w:gz") as t:
    t.add(f"{HOME}/.9router", arcname=".9router",
          filter=lambda ti: None if ("/logs/" in ti.name or "/runtime/" in ti.name or ti.name.endswith((".shm", ".wal"))) else ti)
    t.add(f"{HOME}/.cachewatch", arcname=".cachewatch",
          filter=lambda ti: None if ti.name.endswith((".log", ".db-wal", ".db-shm")) else ti)
    for extra in ["/etc/systemd/system/router.service", "/etc/systemd/system/cachewatch.service",
                  "/etc/systemd/system/ttyd.service.d", "/etc/systemd/system/router.service.d",
                  "/etc/systemd/system/v6bridge.service", "/etc/nginx/sites-available/default"]:
        if os.path.exists(extra):
            t.add(extra, arcname="etc" + extra)
# security fix 2026-10-10: encrypt archive before sending to Telegram
ENC = OUT + ".enc"
PW = open(f"{HOME}/.cachewatch/.backup-pw").read().strip().encode()
import subprocess as sp
r = sp.run(["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-iter", "200000",
            "-salt", "-in", OUT, "-out", ENC, "-pass", "stdin"],
           input=PW, capture_output=True)
if r.returncode != 0:
    sys.exit("encrypt failed: " + r.stderr.decode())
size = os.path.getsize(ENC)
os.remove(OUT)
ok = send_file(ENC, f"🔐 Backup 9router+cachewatch {STAMP} (AES-256 encrypted, {size//1024} KB) — decrypt: openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -in <file> -out backup.tar.gz -pass pass:<pw dari ~/.cachewatch/.backup-pw VPS>")
print("sent" if ok else "FAILED", ENC, size)
if ok and size < 45 * 1024 * 1024:
    os.remove(ENC)
