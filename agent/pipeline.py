"""Үндсэн урсгал: kill switch → PII mask → injection guard → LLM ангилал → дүрэм → тикет → major incident → мэдэгдэл."""
from __future__ import annotations

from datetime import datetime, timezone

from . import db
from .classify import classify_message
from .guard import detect_injection
from .major_incident import check_major_incident
from .models import SEC, ProcessResult, Ticket
from .notify import notify
from .pii import mask_pii
from .policy import apply_policy, should_notify
from .priority import due_date
from .sla import run_sla_check


def process_message(text: str, channel: str = "web") -> ProcessResult:
    message_id = db.new_id("MSG")
    masked, found = mask_pii(text.strip())

    if not db.is_agent_enabled():
        db.audit("agent-disabled", f"Агент унтраалттай үед ирсэн мессеж {message_id}")
        return ProcessResult(
            message_id=message_id, masked_text=masked, pii_found=found, injection_detected=False,
            requests=[], major_incidents=[], notifications=[], agent_disabled=True,
            combined_reply="Автомат агент түр унтраалттай байна. Таны мессежийг Service Desk-ийн ажилтан гараар шалгана.",
        )

    injection, matches = detect_injection(masked)
    if injection:
        db.audit("prompt-injection", f'{message_id}: {", ".join(matches)} — "{masked[:200]}"')
    if found:
        db.audit("pii-masked", f'{message_id}: {", ".join(found)}')

    llm = classify_message(masked)
    now = datetime.now(timezone.utc)
    tickets: list[Ticket] = []
    notifications = []
    majors = []

    for req in llm.requests:
        fields = apply_policy(req, injection, matches, masked)
        if "prompt-injection" in fields["flags"] and not injection:
            db.audit("prompt-injection", f'{message_id}: LLM илрүүлэв — "{masked[:200]}"')
        open_ticket = fields["priority"] and fields["status"] not in ("Шийдвэрлэсэн", "Татгалзсан")
        ticket = Ticket(
            id=db.new_id("SD"),
            message_id=message_id,
            channel=channel,
            masked_text=masked,
            due_at=due_date(fields["priority"], now).isoformat() if open_ticket else None,
            created_at=now.isoformat(),
            updated_at=now.isoformat(),
            **fields,
        )
        db.insert_ticket(ticket)

        mi = check_major_incident(ticket)
        if mi:
            info, mi_notifications = mi
            majors.append(info)
            notifications.extend(mi_notifications)
            ticket.reply += (
                f"\n\nℹ️ {ticket.location} салбараас ижил төрлийн олон хүсэлт ирсэн тул өргөн хүрээний доголдол "
                f"({info['parent_id']}) гэж бүртгэгдсэн. Хариуцсан баг ажиллаж байна, 30 минут тутам шинэчлэл мэдээлнэ (KB-08)."
            )
            if "KB-08" not in ticket.kb_ids:
                ticket.kb_ids.append("KB-08")
            db.update_ticket(ticket)

        if should_notify(ticket.priority, ticket.type):
            target = SEC if ticket.type == "Security" else ticket.team
            notifications.append(notify(
                f"{ticket.priority or ''} {ticket.type}".strip(), target,
                f"{ticket.id}: {ticket.summary}\nШийдвэр: {ticket.decision}\n{ticket.l2_note or ''}", ticket.id,
            ))
        tickets.append(ticket)

    # Тусдаа cron байхгүй тул мессеж бүрийн дараа SLA шалгана
    run_sla_check()

    if len(tickets) == 1:
        combined = tickets[0].reply
    else:
        combined = "\n\n".join(f"{i}. {t.summary}\n{t.reply}" for i, t in enumerate(tickets, 1))

    return ProcessResult(
        message_id=message_id,
        masked_text=masked,
        pii_found=found,
        injection_detected=injection or any("prompt-injection" in t.flags for t in tickets),
        requests=tickets,
        combined_reply=combined,
        major_incidents=majors,
        notifications=notifications,
    )
