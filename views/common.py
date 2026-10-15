"""Хуудсуудын дундын туслах функцууд."""
from datetime import datetime

import streamlit as st

from agent.config import setting

PRIORITY_COLOR = {"P1": "red", "P2": "orange", "P3": "yellow", "P4": "green"}
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
