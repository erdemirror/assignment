"""Хуудсуудын дундын туслах функцууд."""
from datetime import datetime

import streamlit as st

from agent.config import setting

PRIORITY_COLOR = {"P1": "red", "P2": "orange", "P3": "yellow", "P4": "green"}
PRIORITY_DOT = {"P1": "🔴", "P2": "🟠", "P3": "🟡", "P4": "🟢"}
DECISION_COLOR = {"Хариулах": "green", "Шилжүүлэх": "blue", "Татгалзах": "red", "Тодруулах": "violet"}


def badge(text: str, color: str = "gray") -> str:
    return f":{color}-badge[{text}]"


def fmt_time(iso: str | None) -> str:
    if not iso:
        return "—"
    return datetime.fromisoformat(iso).astimezone().strftime("%m-%d %H:%M")


def admin_unlocked() -> bool:
    """ADMIN_PASSWORD тохируулсан бол нууц үг шаардана (local туршилтад тохируулаагүй бол нээлттэй)."""
    expected = setting("ADMIN_PASSWORD")
    if not expected:
        return True
    pw = st.text_input("Админ нууц үг", type="password", key="admin_pw")
    return pw == expected


def page_header(icon: str, title: str, caption: str) -> None:
    st.markdown(f"## {icon} {title}")
    st.caption(caption)


def ticket_stats() -> dict:
    """Хуудсуудын дээд талд харуулах товч статистик."""
    from agent import db
    from agent.models import OPEN_STATUSES

    tickets = [t for t in db.list_tickets(500) if not t.is_parent]
    today = datetime.now().astimezone().date()
    open_ = [t for t in tickets if t.status in OPEN_STATUSES]
    return {
        "today": sum(datetime.fromisoformat(t.created_at).astimezone().date() == today for t in tickets),
        "open": len(open_),
        "p1": sum(t.priority == "P1" for t in open_),
        "security": sum(t.type == "Security" for t in tickets),
        "auto": sum(t.decision == "Хариулах" for t in tickets),
        "total": len(tickets),
    }
