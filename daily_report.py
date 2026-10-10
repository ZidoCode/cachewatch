#!/usr/bin/env python3
"""Daily cachewatch report -> Telegram. Reads bot token + chat id from ~/.hermes/.env"""
import json
import os
import sqlite3
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

DB = os.path.expanduser("~/.cachewatch/cachewatch.db")

env = {}
with open(os.path.expanduser("~/.hermes/.env")) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip().strip('"').strip("'")

TOKEN = env.get("TELEGRAM_BOT_TOKEN")
CHAT = env.get("TELEGRAM_HOME_CHANNEL")
if not TOKEN or not CHAT:
    raise SystemExit("missing TELEGRAM_BOT_TOKEN/TELEGRAM_HOME_CHANNEL in ~/.hermes/.env")

# UTC day = yesterday (report generated shortly after midnight UTC; CST=UTC+8, so
# generate at 17:05 UTC to cover the local day). We report the LAST full local day.
now = datetime.now(timezone(timedelta(hours=8)))
day = (now - timedelta(days=1)).strftime("%Y-%m-%d")

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
rows = conn.execute(
    """SELECT model, SUM(prompt_tokens) p, SUM(cached_tokens) c,
              SUM(completion_tokens) o, COUNT(*) n
       FROM usage WHERE substr(ts,1,10)=? GROUP BY model ORDER BY p DESC""",
    (day,),
).fetchall()

tp = sum(r["p"] or 0 for r in rows)
tc = sum(r["c"] or 0 for r in rows)
tn = sum(r["n"] for r in rows)
pct = (100.0 * tc / tp) if tp else 0.0

lines = [f"⚡ *cachewatch — {day}*", ""]
if not rows:
    lines.append("Tidak ada request tercatat kemarin.")
else:
    lines.append(f"Total: {tn} request · {tp:,} prompt tok · {tc:,} cached · *{pct:.1f}% hit*")
    lines.append("")
    for r in rows[:6]:
        m = r["model"] or "(unknown)"
        p, c = r["p"] or 0, r["c"] or 0
        pc = (100.0 * c / p) if p else 0.0
        lines.append(f"• `{m}` — {r['n']}x · {p:,} tok · hit {pc:.1f}%")
    lines.append("")
    # simple saving estimate: cached tokens ~ billed at fraction of price (varies; use 10x diff)
    lines.append(f"💡 Token ke-cache kemarin: *{tc:,}* — di banyak provider dibill ±10% lebih murah.")

text = "\n".join(lines)
url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
data = urllib.parse.urlencode({
    "chat_id": CHAT, "text": text, "parse_mode": "Markdown",
}).encode()
req = urllib.request.Request(url, data=data)
resp = urllib.request.urlopen(req, timeout=30)
print(resp.status, resp.read()[:200])
