"""Тикетүүд: агентын шийдвэрийг ажилтан хянаж засна (хүний хяналт)."""
import streamlit as st

from agent import db
from agent.models import DECISIONS, PRIORITIES, STATUSES, TEAMS, TICKET_TYPES
from views.common import admin_unlocked, fmt_time

st.subheader("Тикетүүд")
st.caption(
    "Агентын шийдвэрийг ажилтан эндээс хянаж засна. Хадгалалт: "
    + ("**Postgres**" if db.backend() == "postgres" else "**SQLite** (local файл)")
)

tickets = db.list_tickets(300)
if not tickets:
    st.info("Тикет алга")
    st.stop()

children = {}
for t in tickets:
    if t.parent_id:
        children[t.parent_id] = children.get(t.parent_id, 0) + 1

rows = [
    {
        "ID": t.id,
        "Цаг": fmt_time(t.created_at),
        "Агуулга": t.summary,
        "Төрөл": t.type,
        "Эрэмбэ": t.priority or "—",
        "Баг": t.team,
        "Шийдвэр": t.decision,
        "Төлөв": t.status,
        "KB": ", ".join(t.kb_ids) or "—",
        "Байршил": t.location,
        "Parent": f"🚨 {children.get(t.id, 0)} холбоос" if t.is_parent else (t.parent_id or ""),
        "SLA": fmt_time(t.due_at),
        "Хүн засав": "✓" if t.overridden_by_human else "",
    }
    for t in tickets
]
st.dataframe(rows, width="stretch", hide_index=True)

st.divider()
st.markdown("#### Тикет нээж засах")
selected = st.selectbox("Тикет", [t.id for t in tickets], format_func=lambda i: f"{i} — {next(t.summary for t in tickets if t.id == i)}")
t = db.get_ticket(selected)

c1, c2 = st.columns(2)
with c1:
    st.markdown(f"**Мессеж (нууцалсан):** {t.masked_text}")
    st.markdown("**Агентын хариу:**")
    st.text(t.reply)
    if t.l2_note:
        st.markdown("**L2 тэмдэглэл:**")
        st.text(t.l2_note)
    if t.policy_notes:
        st.markdown("**Дүрэм:** " + "; ".join(t.policy_notes))
    if t.flags:
        st.markdown("**Тэмдэглэгээ:** " + ", ".join(t.flags))

with c2:
    if admin_unlocked():
        with st.form("edit"):
            new_type = st.selectbox("Төрөл", TICKET_TYPES, index=TICKET_TYPES.index(t.type))
            prio_opts = ["—", *PRIORITIES]
            new_prio = st.selectbox("Эрэмбэ", prio_opts, index=prio_opts.index(t.priority or "—"))
            new_team = st.selectbox("Баг", TEAMS, index=TEAMS.index(t.team))
            new_dec = st.selectbox("Шийдвэр", DECISIONS, index=DECISIONS.index(t.decision))
            new_status = st.selectbox("Төлөв", STATUSES, index=STATUSES.index(t.status))
            if st.form_submit_button("Хадгалах", type="primary"):
                new_prio = None if new_prio == "—" else new_prio
                changes = [
                    f"{name} {old}→{new}"
                    for name, old, new in [
                        ("type", t.type, new_type), ("priority", t.priority, new_prio), ("team", t.team, new_team),
                        ("decision", t.decision, new_dec), ("status", t.status, new_status),
                    ]
                    if old != new
                ]
                if changes:
                    t.type, t.priority, t.team, t.decision, t.status = new_type, new_prio, new_team, new_dec, new_status
                    t.overridden_by_human = True
                    t.updated_at = db.now_iso()
                    db.update_ticket(t)
                    db.audit("human-override", f"{t.id}: {'; '.join(changes)}")
                    st.success("Хадгаллаа")
                    st.rerun()
    else:
        st.caption("Засахын тулд админ нууц үгээ оруулна уу.")
