"""SLA хяналт (3.9): P1/P2 нь 75% өнгөрөхөд, P3 нь хэтэрсэн үед сануулга илгээнэ."""
from __future__ import annotations

from datetime import datetime, timezone

from . import db
from .notify import notify
from .models import Ticket


def progress(t: Ticket, now: datetime | None = None) -> float:
    if not t.due_at:
        return 0.0
    now = now or datetime.now(timezone.utc)
    start, due = datetime.fromisoformat(t.created_at), datetime.fromisoformat(t.due_at)
    total = max((due - start).total_seconds(), 1)
    return (now - start).total_seconds() / total


def sla_overview() -> list[dict]:
    rows = [
        {"id": t.id, "priority": t.priority, "summary": t.summary, "status": t.status,
         "team": t.team, "progress": progress(t), "due_at": t.due_at}
        for t in db.open_tickets() if t.due_at
    ]
    return sorted(rows, key=lambda r: r["progress"], reverse=True)


def run_sla_check() -> list[str]:
    warned = []
    for t in db.open_tickets():
        # P4-д удирдлагад мэдээлэх шаардлагагүй (SLA хүснэгт)
        if not t.due_at or t.sla_warned or t.priority in (None, "P4"):
            continue
        p = progress(t)
        threshold = 0.75 if t.priority in ("P1", "P2") else 1.0
        if p < threshold:
            continue
        label = "SLA ХЭТЭРСЭН" if p >= 1 else "SLA 75% өнгөрсөн"
        notify(label, f"{t.team} + Service Desk ахлах",
               f"{t.id} ({t.priority}): {t.summary}\nТөлөв: {t.status}\nХугацаа: {t.due_at}", t.id)
        t.sla_warned = True
        t.updated_at = db.now_iso()
        db.update_ticket(t)
        warned.append(t.id)
    return warned
