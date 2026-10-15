"""Мэдэгдлийг үргэлж DB-д бүртгэнэ; Telegram тохируулсан бол тэнд бас илгээнэ."""
from __future__ import annotations

import json
import urllib.request

from . import db
from .config import setting
from .models import Notification


def _send_telegram(text: str) -> bool:
    token, chat_id = setting("TELEGRAM_BOT_TOKEN"), setting("TELEGRAM_CHAT_ID")
    if not (token and chat_id):
        return False
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=json.dumps({"chat_id": chat_id, "text": text}).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as res:
            return res.status == 200
    except OSError:
        return False


def notify(kind: str, target: str, text: str, ticket_id: str | None) -> Notification:
    delivered = _send_telegram(f"🔔 [{kind}] → {target}\n{text}")
    n = Notification(
        id=db.new_id("NTF"), ticket_id=ticket_id, kind=kind, target=target,
        text=text, delivered=delivered, created_at=db.now_iso(),
    )
    db.insert_notification(n)
    return n
