"""Хяналт: kill switch, SLA явц, мэдэгдлүүд, аудит лог."""
import streamlit as st

from agent import db
from agent.classify import model_name, provider
from agent.config import setting
from agent.sla import run_sla_check, sla_overview
from views.common import PRIORITY_COLOR, admin_unlocked, badge, fmt_time

# Тусдаа cron байхгүй тул хуудас нээгдэх бүрт SLA шалгана
run_sla_check()

c1, c2 = st.columns(2)
with c1:
    with st.container(border=True):
        st.subheader("Агентын хяналт")
        st.caption("Агентыг унтраавал бүх мессеж автоматаар боловсруулагдахгүй, ажилтан гараар шалгана.")
        enabled = db.is_agent_enabled()
        st.markdown("🟢 **Агент идэвхтэй**" if enabled else "🔴 **Агент унтраалттай**")
        if admin_unlocked():
            b1, b2 = st.columns(2)
            if b1.button("⏻ Агентыг унтраах" if enabled else "⏻ Агентыг асаах", type="primary", width="stretch"):
                db.set_setting("agent_enabled", "false" if enabled else "true")
                db.audit("kill-switch", "Агентыг унтраав" if enabled else "Агентыг асаав")
                st.rerun()
            if b2.button("SLA шалгах", width="stretch"):
                warned = run_sla_check()
                st.success(f"Сануулга илгээсэн: {', '.join(warned) or 'алга'}")

with c2:
    with st.container(border=True):
        st.subheader("Системийн төлөв")
        st.markdown("\n".join([
            f"- LLM: {provider()} / `{model_name()}` "
            f"{'✅' if setting('GEMINI_API_KEY' if provider() == 'gemini' else 'ANTHROPIC_API_KEY') else '❌ API түлхүүр алга'}",
            f"- Хадгалалт: {'✅ Postgres' if db.backend() == 'postgres' else '⚠️ SQLite (local файл)'}",
            f"- Telegram мэдэгдэл: {'✅ идэвхтэй' if setting('TELEGRAM_BOT_TOKEN') and setting('TELEGRAM_CHAT_ID') else '⚠️ тохируулаагүй — зөвхөн доорх бүртгэлд'}",
        ]))

with st.container(border=True):
    st.subheader("SLA хяналт (нээлттэй тикетүүд)")
    sla = sla_overview()
    if not sla:
        st.caption("Нээлттэй тикет алга")
    for s in sla:
        p = s["progress"]
        icon = "🔴" if p >= 1 else "🟠" if p >= 0.75 else "🟢"
        st.markdown(f"{badge(s['priority'], PRIORITY_COLOR.get(s['priority'], 'gray'))} `{s['id']}` {s['summary']} — {icon} {round(p * 100)}% · {fmt_time(s['due_at'])}")
        st.progress(min(1.0, p))

n_col, a_col = st.columns(2)
with n_col:
    st.subheader("🔔 Мэдэгдлүүд")
    notifications = db.list_notifications(100)
    if not notifications:
        st.caption("Алга")
    for n in notifications:
        with st.container(border=True):
            st.markdown(f"**{n.kind}** → {n.target} · {fmt_time(n.created_at)} {'· Telegram ✓' if n.delivered else ''}")
            st.text(n.text)

with a_col:
    st.subheader("🛡️ Аудит лог")
    st.caption("Prompt injection, PII нууцлалт, хүний засвар, kill switch")
    entries = db.list_audit(100)
    if not entries:
        st.caption("Алга")
    for a in entries:
        color = "red" if a["kind"] == "prompt-injection" else "gray"
        st.markdown(f"{badge(a['kind'], color)} {fmt_time(a['created_at'])}  \n{a['detail']}")
