"""KB-08: 15 минутын дотор ижил салбар/үйлчилгээнээс ≥3 ижил төрлийн хүсэлт → нэг parent P1 тикет."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from . import db
from .models import L1, NET, Notification, Ticket
from .notify import notify
from .priority import due_date

WINDOW = timedelta(minutes=15)
THRESHOLD = 3
# Major incident болж болох үйлчилгээнүүд (хувь хэрэглэгчийн асуудал, эрх, аюулгүй байдал биш)
ELIGIBLE = {"branch_connectivity", "vpn_client", "core_system", "loan_system", "email", "meet", "network", "printer"}
# VPN client, салбарын холболт, Core систем рүү нэвтрэх боломжгүй гэдэг нь салбарын түвшинд нэг шалтгаантай байх магадлалтай
GROUP = {"branch_connectivity": "connectivity", "vpn_client": "connectivity", "core_system": "connectivity", "network": "connectivity"}


def _group(service: str) -> str:
    return GROUP.get(service, service)


def check_major_incident(ticket: Ticket) -> tuple[dict, list[Notification]] | None:
    """Шинэ тикетийг шалгаж, шаардлагатай бол parent үүсгэх эсвэл одоо байгаа parent-д холбоно."""
    if ticket.service not in ELIGIBLE or ticket.location == "Тодорхойгүй" or ticket.is_parent:
        return None

    now = datetime.now(timezone.utc)
    recent = db.tickets_since((now - WINDOW).isoformat())
    same = [
        t for t in recent
        if not t.is_parent and t.location == ticket.location and t.service in ELIGIBLE and _group(t.service) == _group(ticket.service)
    ]
    if all(t.id != ticket.id for t in same):
        same.append(ticket)

    # Өмнө үүссэн нээлттэй parent байвал түүнд холбоно
    existing = next(
        (t for t in recent if t.is_parent and t.location == ticket.location
         and _group(t.service) == _group(ticket.service) and t.status != "Хаагдсан"),
        None,
    )
    if existing:
        ticket.parent_id = existing.id
        info = {"parent_id": existing.id, "location": ticket.location, "count": len(same), "created": False}
        return info, []
    if len(same) < THRESHOLD:
        return None

    ids = ", ".join(t.id for t in same)
    parent = Ticket(
        id=db.new_id("MI"),
        message_id=ticket.message_id,
        channel="system",
        masked_text=f"Major incident: {ticket.location} — {len(same)} хүсэлт 15 минутад",
        summary=f"MAJOR INCIDENT: {ticket.location} салбар — {ticket.summary}",
        type="Incident", impact="Өндөр", urgency="Өндөр", priority="P1",
        team=NET if ticket.team == L1 else ticket.team,
        service=ticket.service, decision="Шилжүүлэх", kb_ids=["KB-08"],
        requester=None, affected_user=None, location=ticket.location, time_info=None,
        reply=(
            f"{ticket.location} салбарт өргөн хүрээний доголдол илэрсэн бөгөөд хариуцсан баг шалгаж байна. "
            "Бид 30 минут тутам шинэчлэл мэдээлнэ. Дахин тикет нээх шаардлагагүй."
        ),
        l2_note=f"KB-08: 15 минутад {len(same)} ижил хүсэлт ({ids}). Салбарын холболт/үйлчилгээг шалгана уу.",
        status="L2-т шилжсэн",
        flags=["major-incident"],
        policy_notes=["KB-08 major incident автоматаар үүсгэв"],
        is_parent=True,
        due_at=due_date("P1", now).isoformat(),
        created_at=now.isoformat(),
        updated_at=now.isoformat(),
    )
    db.insert_ticket(parent)
    for child in same:
        child.parent_id = parent.id
        child.updated_at = now.isoformat()
        if child is not ticket:
            db.update_ticket(child)
    ticket.parent_id = parent.id

    body = f"{parent.summary}\nParent: {parent.id}\n{parent.l2_note}"
    notifications = [
        notify("MAJOR INCIDENT P1", "Service Desk ахлах", body, parent.id),
        notify("MAJOR INCIDENT P1", parent.team, body, parent.id),
        notify("Ерөнхий мэдэгдэл", f"Өртсөн хэрэглэгчид ({len(same)})", parent.reply, parent.id),
    ]
    info = {"parent_id": parent.id, "location": parent.location, "count": len(same), "created": True}
    return info, notifications
