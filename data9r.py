#!/usr/bin/env python3
"""
data9r — read-only data layer for the ops dashboard.
Reads 9router's SQLite (usageHistory, usageDaily, providerConnections, apiKeys,
combos) + cachewatch's own DB. No writes, WAL-safe (immutable read is fine while
9router runs because WAL allows concurrent readers).
"""
import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone

R9_DB = "/home/agentuser/.9router/db/data.sqlite"
CW_DB = os.path.expanduser("~/.cachewatch/cachewatch.db")
CST = timezone(timedelta(hours=8))


def _q(db, sql, args=()):
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=5)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(sql, args)]
    finally:
        conn.close()


def summary():
    today = datetime.now(CST).strftime("%Y-%m-%d")
    rows = _q(R9_DB, "SELECT data FROM usageDaily WHERE dateKey=?", (today,))
    d = json.loads(rows[0]["data"]) if rows else {}
    hist = _q(
        R9_DB,
        "SELECT status, COUNT(*) n FROM usageHistory "
        "WHERE substr(timestamp,1,10)=? GROUP BY status",
        (today,),
    )
    ok = sum(r["n"] for r in hist if r["status"] == "ok")
    tot = sum(r["n"] for r in hist) or 1
    return {
        "date": today,
        "requests": d.get("requests", 0),
        "ok_pct": round(100.0 * ok / tot, 1),
        "tokens": (d.get("promptTokens", 0) + d.get("completionTokens", 0)),
        "cost": round(d.get("cost", 0), 4),
        "cached_tokens": d.get("cachedTokens", 0),
    }


def hourly():
    """Requests per hour for the last 24h from usageHistory."""
    since = (datetime.now(CST) - timedelta(hours=24)).strftime("%Y-%m-%dT%H")
    rows = _q(
        R9_DB,
        "SELECT substr(timestamp,1,13) h, COUNT(*) n FROM usageHistory "
        "GROUP BY h ORDER BY h",
    )
    out = [(r["h"], r["n"]) for r in rows if r["h"] >= since]
    return out


def providers():
    rows = _q(
        R9_DB,
        "SELECT provider, name, email, authType, priority, isActive, data "
        "FROM providerConnections ORDER BY priority",
    )
    out = []
    for r in rows:
        d = {}
        try:
            d = json.loads(r.pop("data") or "{}")
        except Exception:
            pass
        q = None
        err = d.get("lastError")
        out.append({
            "provider": r["provider"],
            "name": r["name"],
            "auth": r["authType"],
            "priority": r["priority"],
            "active": bool(r["isActive"]),
            "status": d.get("testStatus", "unknown"),
            "error": err,
            "rate_limited_until": d.get("rateLimitedUntil"),
        })
    return out


def keys():
    rows = _q(R9_DB, "SELECT name, key, isActive, createdAt FROM apiKeys WHERE isActive=1")
    return [{"name": r["name"], "key": r["key"], "created": r["createdAt"][:10]} for r in rows]


def models_today():
    today = datetime.now(CST).strftime("%Y-%m-%d")
    rows = _q(R9_DB, "SELECT data FROM usageDaily WHERE dateKey=?", (today,))
    if not rows:
        return []
    d = json.loads(rows[0]["data"])
    out = []
    for k, v in (d.get("byModel") or {}).items():
        p = v.get("promptTokens") or 0
        c = v.get("cachedTokens") or 0
        out.append({
            "model": v.get("rawModel", k),
            "provider": v.get("provider", "?"),
            "requests": v.get("requests", 0),
            "prompt": p,
            "cached": c,
            "completion": v.get("completionTokens", 0),
            "cost": round(v.get("cost", 0), 4),
            "hit_pct": round(100.0 * c / p, 1) if p else 0.0,
        })
    out.sort(key=lambda x: -x["prompt"])
    return out


def recent_logs(limit=30):
    rows = _q(
        R9_DB,
        "SELECT timestamp, provider, model, promptTokens, completionTokens, cost, status "
        "FROM usageHistory ORDER BY id DESC LIMIT ?",
        (limit,),
    )
    return [{
        "ts": r["timestamp"][11:19],
        "provider": r["provider"],
        "model": r["model"],
        "prompt": r["promptTokens"] or 0,
        "completion": r["completionTokens"] or 0,
        "cost": r["cost"] or 0,
        "status": r["status"],
    } for r in rows]


def cw_stats():
    rows = _q(
        CW_DB,
        "SELECT model, SUM(prompt_tokens) p, SUM(cached_tokens) c, COUNT(*) n "
        "FROM usage GROUP BY model ORDER BY p DESC",
    )
    out = []
    for r in rows:
        p, c = r["p"] or 0, r["c"] or 0
        out.append({
            "model": r["model"] or "unknown",
            "requests": r["n"], "prompt": p, "cached": c,
            "hit_pct": round(100.0 * c / p, 1) if p else 0.0,
        })
    return out


def usage_days(days=7):
    since = (datetime.now(CST) - timedelta(days=days - 1)).strftime("%Y-%m-%d")
    rows = _q(
        R9_DB,
        "SELECT dateKey, data FROM usageDaily WHERE dateKey>=? ORDER BY dateKey",
        (since,),
    )
    out = []
    for r in rows:
        d = json.loads(r["data"])
        out.append({
            "date": r["dateKey"],
            "requests": d.get("requests", 0),
            "tokens": d.get("promptTokens", 0) + d.get("completionTokens", 0),
            "cached": d.get("cachedTokens", 0),
            "cost": round(d.get("cost", 0), 4),
        })
    return out
