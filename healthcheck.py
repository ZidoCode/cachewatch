#!/usr/bin/env python3
"""Self-healing: ensure cachewatch/router/ngrok are up; restart if down; alert via Telegram."""
import os
import subprocess
import urllib.parse
import urllib.request

SERVICES = ["cachewatch", "router", "ngrok", "ttyd", "9router"]
CHECK_URL = "http://127.0.0.1:20130/_cw/health"


def env_from(path):
    env = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def send(text):
    env = env_from(os.path.expanduser("~/.hermes/.env"))
    token, chat = env.get("TELEGRAM_BOT_TOKEN"), env.get("TELEGRAM_HOME_CHANNEL")
    if not token or not chat:
        return
    data = urllib.parse.urlencode({"chat_id": chat, "text": text}).encode()
    try:
        urllib.request.urlopen(urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data), timeout=20)
    except Exception:
        pass


def active(svc):
    try:
        r = subprocess.run(["systemctl", "is-active", svc], capture_output=True, text=True, timeout=15)
        return r.stdout.strip() == "active"
    except Exception:
        return False


problems = []
restarted = []
for s in SERVICES:
    if not active(s):
        problems.append(s)
        try:
            subprocess.run(["sudo", "systemctl", "restart", s], capture_output=True, text=True, timeout=60)
            if active(s):
                restarted.append(s)
        except Exception:
            pass

if problems:
    msg = "⚠️ ops hub health-check:\n"
    msg += "Down: " + ", ".join(problems) + "\n"
    if restarted:
        msg += "Auto-restart OK: " + ", ".join(restarted)
    else:
        msg += "Auto-restart GAGAL — cek manual."
    send(msg)
    print(msg)
else:
    print("all services active")
