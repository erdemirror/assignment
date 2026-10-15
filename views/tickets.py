"""Тикетүүд: агентын шийдвэрийг ажилтан хянаж засна (хүний хяналт)."""
import streamlit as st

from agent import db
from agent.models import DECISIONS, OPEN_STATUSES, PRIORITIES, STATUSES, TEAMS, TICKET_TYPES
from views.common import PRIORITY_DOT, admin_unlocked, fmt_time, page_header, ticket_stats

page_header(
    "🎫", "Тикетүүд",
    "Агентын шийдвэрийг ажилтан эндээс хянаж засна. Хадгалалт: "
    + ("Postgres" if db.backend() == "postgres" else "SQLite (local файл)"),
)

tickets = db.list_tickets(300)
if not tickets:
    st.info("Тикет алга. \"Агент турших\" хуудаснаас мессеж илгээнэ үү.")
    st.stop()

stats = ticket_stats()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Нийт", stats["total"], border=True)
c2.metric("Нээлттэй", stats["open"], border=True)
c3.metric("Нээлттэй P1", stats["p1"], border=True)
c4.metric("Аюулгүй байдал", stats["security"], border=True)

# ---------- Шүүлтүүр ----------
f1, f2, f3 = st.columns([2, 2, 3])
scope = f1.segmented_control("Төлөв", ["Бүгд", "Нээлттэй", "Хаагдсан"], default="Бүгд")
prio = f2.pills("Эрэмбэ", PRIORITIES, selection_mode="multi")
teams = f3.multiselect("Баг", TEAMS, placeholder="Бүх баг")

children: dict[str, int] = {}
for t in tickets:
    if t.parent_id:
        children[t.parent_id] = children.get(t.parent_id, 0) + 1


def visible(t) -> bool:
    if scope == "Нээлттэй" and t.status not in OPEN_STATUSES:
        return False
    if scope == "Хаагдсан" and t.status in OPEN_STATUSES:
        return False
    if prio and t.priority not in prio:
        return False
    return not teams or t.team in teams


shown = [t for t in tickets if visible(t)]
st.dataframe(
    [
        {
            "ID": ("🚨 " if t.is_parent else "") + t.id,
            "Цаг": fmt_time(t.created_at),
            "Эрэмбэ": f"{PRIORITY_DOT.get(t.priority, '⚪')} {t.priority or '—'}",
            "Агуулга": t.summary,
            "Төрөл": t.type,
            "Баг": t.team,
            "Шийдвэр": t.decision,
            "Төлөв": t.status,
            "KB": ", ".join(t.kb_ids) or "—",
            "Байршил": t.location,
            "Parent": f"{children.get(t.id, 0)} холбоос" if t.is_parent else (t.parent_id or ""),
            "SLA": fmt_time(t.due_at),
            "Хүн засав": "✏️" if t.overridden_by_human else "",
        }
        for t in shown
    ],
    column_config={"Агуулга": st.column_config.TextColumn(width="large")},
    width="stretch",
    hide_index=True,
)
st.caption(f"{len(shown)} / {len(tickets)} тикет харагдаж байна")

# ---------- Дэлгэрэнгүй ба засвар ----------
st.markdown("#### Тикет нээж засах")
if not shown:
    st.stop()
selected = st.selectbox("Тикет", [t.id for t in shown], format_func=lambda i: f"{i} — {next(t.summary for t in shown if t.id == i)}")
t = db.get_ticket(selected)

c1, c2 = st.columns([3, 2], gap="large")
with c1:
    with st.container(border=True):
        st.markdown("**Мессеж (нууцалсан)**")
        st.markdown(f"> {t.masked_text}")
        st.markdown("**Агентын хариу**")
        st.markdown(t.reply)
        if t.l2_note:
            st.markdown("**L2 тэмдэглэл**")
            st.code(t.l2_note, language=None, wrap_lines=True)
        if t.policy_notes:
            st.caption("🛡️ " + " · ".join(t.policy_notes))
        if t.flags:
            st.caption("🏷️ " + ", ".join(t.flags))

with c2:
    with st.container(border=True):
        st.markdown("**Шийдвэр засах**")
        if admin_unlocked():
            with st.form("edit", border=False):
                new_type = st.selectbox("Төрөл", TICKET_TYPES, index=TICKET_TYPES.index(t.type))
                prio_opts = ["—", *PRIORITIES]
                new_prio = st.selectbox("Эрэмбэ", prio_opts, index=prio_opts.index(t.priority or "—"))
                new_team = st.selectbox("Баг", TEAMS, index=TEAMS.index(t.team))
                new_dec = st.selectbox("Шийдвэр", DECISIONS, index=DECISIONS.index(t.decision))
                new_status = st.selectbox("Төлөв", STATUSES, index=STATUSES.index(t.status))
                if st.form_submit_button("Хадгалах", type="primary", width="stretch"):
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
                        st.toast("Хадгаллаа ✅")
                        st.rerun()
        else:
            st.caption("Засахын тулд админ нууц үгээ оруулна уу.")
