# cachewatch

**See how much of your LLM bill is cache — and how much is waste.**

cachewatch is a transparent, local-first observability proxy for OpenAI-compatible LLM routers (9Router, LiteLLM, OpenRouter, etc). It sits between your AI agent and your provider, records every request's token usage into SQLite, and shows you the one number nobody's dashboard shows: **your prompt cache hit rate, per model, per day.**

## Why

Prompt caching discounts repeated input prefixes by up to 90% — but only if your prompt prefix is byte-stable. One dynamic token (a timestamp, a session ID) near the top of your system prompt voids the entire cache, and **you pay full price with zero visible signal**.

Real numbers from this project's own single-VPS setup (free-tier providers, one busy agent):

| Route | Cache hit rate |
|---|---|
| Stable reusable prefix (system prompt + tools) | **92%** |
| Agent turns with dynamic content up front | **~0%** |

Same provider, same model — the only difference is prompt layout.

## What it does

- **Logs every `/v1/*` request**: prompt / cached / completion / total tokens, latency, status, model — into a local SQLite DB
- **Normalizes cache metrics** across providers (OpenAI `cached_tokens`, Anthropic `cache_read_input_tokens`, DeepSeek `prompt_cache_hit_tokens`)
- **Daily Telegram report**: tokens, cached tokens, estimated savings, hit rate per model
- **Health-check + self-healing**: cron watchdog restarts dead services and alerts via Telegram
- **Live dashboard** (`/cw/ops`): network map, usage stats, service status
- **Full 9Router dashboard passthrough** — proxy the upstream's own UI at `/dashboard`
- **Weekly backup** of config + DB to Telegram

## Quick start

Requires Python 3.10+, a Linux box (VPS/home server) and an upstream OpenAI-compatible endpoint.

```bash
git clone https://github.com/ZidoCode/cachewatch.git
cd cachewatch
```

Point cachewatch at your upstream router:

```bash
UPSTREAM=http://127.0.0.1:20128 python3 cachewatch.py
```

Then point your agent's `base_url` at cachewatch instead of the router:

```yaml
# e.g. Hermes / OpenAI SDK config
base_url: http://127.0.0.1:20130/v1
```

Every request is now logged to `~/.cachewatch/cachewatch.db`. Check your hit rate:

```bash
sqlite3 ~/.cachewatch/cachewatch.db "
  SELECT model,
         ROUND(100.0*SUM(cached_tokens)/SUM(prompt_tokens),1) AS hit_pct,
         SUM(prompt_tokens) AS prompt, SUM(cached_tokens) AS cached
  FROM usage GROUP BY model ORDER BY prompt DESC;"
```

### Optional: systemd + watchdog + daily report

```bash
sudo cp cachewatch.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now cachewatch
# watchdog (restart dead services, Telegram alert):
#   every 5 min via cron; reads TELEGRAM_BOT_TOKEN / TELEGRAM_HOME_CHANNEL from your env file
# daily report (yesterday's usage + hit rate):
python3 daily_report.py
```

## Files

| File | What |
|---|---|
| `cachewatch.py` | The proxy: `/v1/*` forwarding + usage logging + dashboard passthrough |
| `router.py` | Optional edge router: one public port → cachewatch / dashboard / web terminal |
| `ops_v3.py` | Self-contained ops dashboard (network map, usage, health) |
| `healthcheck.py` | Cron watchdog: auto-restart + Telegram alert |
| `daily_report.py` | Yesterday's usage & cache-hit report → Telegram |
| `backup.py` | Weekly tar.gz of config + DB → Telegram |
| `data9r.py` | Query helpers for the 9Router upstream DB |
| `*.service` | Ready-made systemd units |

## Design notes

- **Local-first**: DB stays on your box; Telegram is only a delivery channel you configure
- **Read-only w.r.t. traffic**: usage fields are parsed from responses, requests are forwarded untouched
- **Provider-agnostic cache parsing**: wherever the "cached" field hides in the usage object, it gets found
- Tested on: 9Router (v0.5.95) with Antigravity & OpenRouter upstreams; Python 3.11; Ubuntu VPS behind Cloudflare Tunnel

## Status

Working, in daily personal use. This is a single-maintainer project — issues and PRs welcome, especially paid-provider cache-metric samples (Anthropic/OpenAI/Gemini response payloads) to broaden the parser tests.

## License

MIT
