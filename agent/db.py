"""Хадгалалт: DATABASE_URL байвал Postgres (Neon), үгүй бол SQLite файл (data/servicedesk.db).

Тикет, мэдэгдэл, аудитыг JSON болгон хадгална — хүснэгтийн бүтэц энгийн, хоёр DB-д адилхан ажиллана.
"""
from __future__ import annotations

import json
import secrets
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path

from .config import setting
from .models import OPEN_STATUSES, Notification, Ticket

SQLITE_PATH = Path(__file__).resolve().parent.parent / "data" / "servicedesk.db"

SCHEMA = [
    "CREATE TABLE IF NOT EXISTS tickets (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, status TEXT NOT NULL, data TEXT NOT NULL)",
    "CREATE INDEX IF NOT EXISTS tickets_created_idx ON tickets (created_at)",
    "CREATE TABLE IF NOT EXISTS notifications (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, data TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS audit_log (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, kind TEXT NOT NULL, detail TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS llm_calls (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, model TEXT NOT NULL, status TEXT NOT NULL)",
]

_initialized = False


def backend() -> str:
    return "postgres" if setting("DATABASE_URL") else "sqlite"


@contextmanager
def _conn():
    global _initialized
    url = setting("DATABASE_URL")
    if url:
        import psycopg

        conn = psycopg.connect(url)
    else:
        SQLITE_PATH.parent.mkdir(exist_ok=True)
        conn = sqlite3.connect(SQLITE_PATH)
    try:
        if not _initialized:
            for stmt in SCHEMA:
                conn.execute(stmt)
            _initialized = True
        yield conn
        conn.commit()
    finally:
        conn.close()


def _q(sql: str) -> str:
    # SQLite "?" ↔ Postgres "%s"
    return sql.replace("?", "%s") if backend() == "postgres" else sql


def _exec(sql: str, params: tuple = ()) -> list[tuple]:
    with _conn() as conn:
        cur = conn.execute(_q(sql), params)
        return cur.fetchall() if cur.description else []


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}-{int(time.time() * 1000):X}{secrets.token_hex(2).upper()}"


# ---------- Тикет ----------
def insert_ticket(t: Ticket) -> None:
    _exec("INSERT INTO tickets (id, created_at, status, data) VALUES (?, ?, ?, ?)",
          (t.id, t.created_at, t.status, json.dumps(t.to_dict(), ensure_ascii=False)))


def update_ticket(t: Ticket) -> None:
    _exec("UPDATE tickets SET status = ?, data = ? WHERE id = ?",
          (t.status, json.dumps(t.to_dict(), ensure_ascii=False), t.id))


def get_ticket(ticket_id: str) -> Ticket | None:
    rows = _exec("SELECT data FROM tickets WHERE id = ?", (ticket_id,))
    return Ticket.from_dict(json.loads(rows[0][0])) if rows else None


def list_tickets(limit: int = 300) -> list[Ticket]:
    rows = _exec("SELECT data FROM tickets ORDER BY created_at DESC LIMIT ?", (limit,))
    return [Ticket.from_dict(json.loads(r[0])) for r in rows]


def tickets_since(since_iso: str) -> list[Ticket]:
    rows = _exec("SELECT data FROM tickets WHERE created_at >= ? ORDER BY created_at DESC", (since_iso,))
    return [Ticket.from_dict(json.loads(r[0])) for r in rows]


def open_tickets() -> list[Ticket]:
    marks = ", ".join("?" for _ in OPEN_STATUSES)
    rows = _exec(f"SELECT data FROM tickets WHERE status IN ({marks})", tuple(OPEN_STATUSES))
    return [Ticket.from_dict(json.loads(r[0])) for r in rows]


# ---------- Мэдэгдэл, аудит, тохиргоо ----------
def insert_notification(n: Notification) -> None:
    _exec("INSERT INTO notifications (id, created_at, data) VALUES (?, ?, ?)",
          (n.id, n.created_at, json.dumps(asdict(n), ensure_ascii=False)))


def list_notifications(limit: int = 100) -> list[Notification]:
    rows = _exec("SELECT data FROM notifications ORDER BY created_at DESC LIMIT ?", (limit,))
    return [Notification(**json.loads(r[0])) for r in rows]


def audit(kind: str, detail: str) -> None:
    _exec("INSERT INTO audit_log (id, created_at, kind, detail) VALUES (?, ?, ?, ?)",
          (new_id("AUD"), now_iso(), kind, detail))


def list_audit(limit: int = 100) -> list[dict]:
    rows = _exec("SELECT created_at, kind, detail FROM audit_log ORDER BY created_at DESC LIMIT ?", (limit,))
    return [{"created_at": r[0], "kind": r[1], "detail": r[2]} for r in rows]


def get_setting(key: str) -> str | None:
    rows = _exec("SELECT value FROM settings WHERE key = ?", (key,))
    return rows[0][0] if rows else None


def set_setting(key: str, value: str) -> None:
    _exec("INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT (key) DO UPDATE SET value = excluded.value",
          (key, value))


def is_agent_enabled() -> bool:
    return get_setting("agent_enabled") != "false"


# ---------- LLM хэрэглээ ----------
def log_llm_call(model: str, status: str) -> None:
    """status: "ok" эсвэл алдааны товч тайлбар ("429 өдөрт 20" г.м.)."""
    _exec("INSERT INTO llm_calls (id, created_at, model, status) VALUES (?, ?, ?, ?)",
          (new_id("LLM"), now_iso(), model, status))


def quota_day_start() -> str:
    # Gemini-ийн өдрийн квот Pacific цагаар шөнө дунд тэглэгддэг
    pacific = datetime.now(ZoneInfo("America/Los_Angeles")).replace(hour=0, minute=0, second=0, microsecond=0)
    return pacific.astimezone(timezone.utc).isoformat()


def llm_usage_today() -> dict[str, dict]:
    rows = _exec("SELECT model, status, created_at FROM llm_calls WHERE created_at >= ? ORDER BY created_at",
                 (quota_day_start(),))
    usage: dict[str, dict] = {}
    for model, status, created_at in rows:
        u = usage.setdefault(model, {"ok": 0, "errors": 0, "last_status": "", "last_at": ""})
        if status == "ok":
            u["ok"] += 1
        else:
            u["errors"] += 1
        u["last_status"], u["last_at"] = status, created_at
    return usage
