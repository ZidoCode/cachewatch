#!/usr/bin/env python3
"""Check current ngrok URL for cachewatch; if changed since last check,
send the new dashboard URL to Telegram. Runs every minute via cron."""
import json
import os
import subprocess
import urllib.parse
import urllib.request

STATE = os.path.expanduser("~/.cachewatch/.url_state")
LOG_URL = "https://api.telegram.org"


def env_from(path):
    env = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def current_url():
    try:
        out = subprocess.run(
            ["sudo", "journalctl", "-u", "cachewatch-ngrok", "--no-pager", "-n", "200"],
            capture_output=True, text=True, timeout=30,
        ).stdout
        urls = []
        for line in out.splitlines():
            if '"url":"' in line:
                try:
                    j = json.loads(line[line.index("{"):])
                    u = j.get("url", "")
                    if "ngrok" in u:
                        urls.append(u)
                except Exception:
                    pass
        return urls[-1] if urls else None
    except Exception:
        return None


def send(text):
    env = env_from(os.path.expanduser("~/.hermes/.env"))
    token, chat = env.get("TELEGRAM_BOT_TOKEN"), env.get("TELEGRAM_HOME_CHANNEL")
    if not token or not chat:
        return
    data = urllib.parse.urlencode({"chat_id": chat, "text": text}).encode()
    urllib.request.urlopen(urllib.request.Request(f"{LOG_URL}/bot{token}/sendMessage", data=data), timeout=30)


cur = current_url()
if not cur:
    raise SystemExit(0)
prev = None
if os.path.exists(STATE):
    prev = open(STATE).read().strip()
if cur != prev:
    open(STATE, "w").write(cur)
    if prev:  # only notify on CHANGE, not first run
        send(f"⚡ cachewatch URL dashboard baru:\n{cur}/_cw/dashboard\n\n(URL ngrok berubah karena tunnel restart)")
    print(f"url: {cur} (prev: {prev})")
else:
    print(f"url unchanged: {cur}")
