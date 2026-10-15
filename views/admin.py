"""Хяналт: kill switch, LLM загвар сонголт, SLA явц, мэдэгдлүүд, аудит лог."""
import streamlit as st

from agent import db
from agent.classify import list_gemini_models, model_name, probe_gemini_model, provider
from agent.config import setting
from agent.sla import run_sla_check, sla_overview
from views.common import PRIORITY_COLOR, admin_unlocked, badge, fmt_time, page_header

page_header("🛡️", "Хяналт", "Агентыг унтраах, LLM загвар сонгох, SLA явц, мэдэгдэл болон аудит лог.")

# Тусдаа cron байхгүй тул хуудас нээгдэх бүрт SLA шалгана
run_sla_check()

# Нууц үгийн талбар нэг л удаа гарна — доорх бүх админ үйлдэлд хамаарна
unlocked = admin_unlocked()

c1, c2 = st.columns(2)
with c1:
    with st.container(border=True):
        st.subheader("Агентын хяналт")
        st.caption("Агентыг унтраавал бүх мессеж автоматаар боловсруулагдахгүй, ажилтан гараар шалгана.")
        enabled = db.is_agent_enabled()
        st.markdown("🟢 **Агент идэвхтэй**" if enabled else "🔴 **Агент унтраалттай**")
        if unlocked:
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

@st.cache_data(ttl=600, show_spinner="Gemini загваруудыг татаж байна…")
def cached_models() -> list[str]:
    return list_gemini_models()


def status_icon(status: str) -> str:
    if not status:
        return "—"
    if status == "ok":
        return "✅ ажиллаж байна"
    return ("🔴 " if status.startswith("429") else "🟠 ") + status


if provider() == "gemini":
    with st.container(border=True):
        st.subheader("🤖 LLM загвар (Gemini)")
        st.caption(
            "Google API үлдэгдэл квотыг харуулдаггүй тул энд манай апп-ын өнөөдрийн хэрэглээг харуулна "
            "(Pacific цагаар шөнө дунд тэглэгдэнэ). Квотын хязгаар 429 алдаа гарах үед л мэдэгдэнэ."
        )
        current = model_name()
        try:
            models = cached_models()
        except Exception as e:
            models = []
            st.error(f"Загваруудын жагсаалт авч чадсангүй: {e}")
        if current not in models:
            models = [current, *models]
        usage = db.llm_usage_today()
        st.dataframe(
            [
                {
                    "Загвар": m,
                    "Идэвхтэй": "⭐" if m == current else "",
                    "Өнөөдөр амжилттай": usage.get(m, {}).get("ok", 0),
                    "Өнөөдөр алдаа": usage.get(m, {}).get("errors", 0),
                    "Сүүлийн төлөв": status_icon(usage.get(m, {}).get("last_status", "")),
                    "Сүүлд": fmt_time(usage.get(m, {}).get("last_at") or None),
                }
                for m in models
            ],
            hide_index=True,
            width="stretch",
        )
        if unlocked:
            choice = st.selectbox("Загвар сонгох", models, index=models.index(current))
            b1, b2, b3 = st.columns(3)
            if b1.button("✔️ Идэвхжүүлэх", type="primary", width="stretch", disabled=choice == current):
                db.set_setting("gemini_model", choice)
                db.audit("model-change", f"{current} → {choice}")
                st.rerun()
            if b2.button("🔍 Сонгосныг шалгах", width="stretch"):
                st.toast(f"{choice}: {status_icon(probe_gemini_model(choice))}")
                st.rerun()
            if b3.button("🔍 Бүгдийг шалгах", width="stretch", help=f"{len(models)} хүсэлт зарцуулна"):
                bar = st.progress(0.0)
                for i, m in enumerate(models):
                    bar.progress(i / len(models), text=f"{m} шалгаж байна…")
                    probe_gemini_model(m)
                st.rerun()
            st.caption("Шалгах бүрт тухайн загварын квотоос 1 хүсэлт зарцуулна.")
        else:
            st.caption("Загвар солихын тулд админ нууц үгээ оруулна уу.")

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
