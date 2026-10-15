"""Тест хуудас: даалгаврын 20 тест мессежийг агентаар ажиллуулж, нарийвчлалыг харуулна."""
import json
import time
from datetime import datetime

import streamlit as st

from agent import db
from agent.classify import model_name, provider
from agent.testsuite import TESTS, run_case, to_markdown
from views.common import admin_unlocked, page_header

COLUMNS = ["ID", "Мессеж", "Ангилал", "Эрэмбэ", "Шийдвэр", "Баг", "KB", "Үнэлгээ", "Хариу"]
COLUMN_CONFIG = {
    "Мессеж": st.column_config.TextColumn(width="medium"),
    "Хариу": st.column_config.TextColumn(width="large"),
    "Үнэлгээ": st.column_config.TextColumn(width="medium"),
}


def show_results(rows: list[dict], header: str) -> None:
    ok = sum(r["Зөв"] for r in rows)
    c1, c2, c3 = st.columns(3)
    c1.metric("Нарийвчлал", f"{round(ok / len(rows) * 100)}%", border=True)
    c2.metric("Зөв", f"{ok} / {len(rows)}", border=True)
    c3.metric("Алдаатай", len(rows) - ok, border=True)
    st.caption(header)
    st.dataframe([{k: r[k] for k in COLUMNS} for r in rows], column_config=COLUMN_CONFIG, hide_index=True, width="stretch")
    st.download_button(
        "⬇️ Тайланд оруулах хүснэгт (Markdown)",
        to_markdown(rows, header),
        file_name="test-results.md",
        mime="text/markdown",
    )


page_header(
    "🧪", "Тест (20 мессеж)",
    "Даалгаврын 7-р хэсгийн 20 тест мессежийг агентаар дараалан ажиллуулж, хүлээгдэж буй үр дүнтэй харьцуулна. "
    "Эргэлзээтэй тохиолдолд үндэслэлтэй хэд хэдэн хувилбарыг зөв гэж тооцно.",
)

with st.expander("Хүлээгдэж буй үр дүн"):
    st.dataframe(
        [
            {
                "ID": tid,
                "Мессеж": text,
                "Төрөл": " / ".join(exp["type"]),
                "Эрэмбэ": " / ".join(p or "—" for p in exp["priority"]),
                "Шийдвэр": " / ".join(exp["decision"]),
                "Баг": " / ".join(exp["team"]),
                "KB": exp.get("kb", "—"),
                "Нэмэлт": ", ".join(
                    x for x in [
                        f"төлөв: {exp['status']}" if exp.get("status") else "",
                        f"≥{exp['min_requests']} хүсэлт" if exp.get("min_requests") else "",
                        "major incident" if exp.get("major") else "",
                    ] if x
                ),
            }
            for tid, text, exp in TESTS
        ],
        hide_index=True,
        width="stretch",
    )

# ---------- Ажиллуулах ----------
with st.container(border=True):
    st.markdown(f"**LLM:** {provider()} / `{model_name()}`")
    ids = [tid for tid, _, _ in TESTS]
    selected = st.multiselect("Ажиллуулах тестүүд", ids, default=ids)
    # Gemini үнэгүй багц минутад цөөн хүсэлт зөвшөөрдөг тул мессеж хооронд хүлээнэ
    delay = st.number_input("Мессеж хоорондын хүлээлт (сек)", 0, 60, 13 if provider() == "gemini" else 0)
    st.caption(
        f"Ойролцоогоор {round(len(selected) * (delay + 4) / 60, 1)} минут. "
        'Үүссэн тикетүүд "Тикетүүд" хуудсанд test сувгаар бүртгэгдэнэ. '
        "T07–T09-ийг дараалуулан ажиллуулбал major incident үүснэ."
    )
    can_run = admin_unlocked()
    start = st.button("▶️ Тест ажиллуулах", type="primary", disabled=not (can_run and selected))
    if not can_run:
        st.caption("Квот хэмнэхийн тулд тест ажиллуулахад админ нууц үг шаардана. Сүүлийн үр дүнг доор харж болно.")

if start:
    cases = [c for c in TESTS if c[0] in selected]
    progress = st.progress(0.0, text="Эхэлж байна…")
    live = st.empty()
    rows: list[dict] = []
    for i, (tid, text, exp) in enumerate(cases):
        if i and delay:
            progress.progress(i / len(cases), text=f"{tid} — квотын хязгаараас болж {delay} сек хүлээж байна…")
            time.sleep(delay)
        progress.progress(i / len(cases), text=f"{tid} ажиллаж байна… ({i + 1}/{len(cases)})")
        rows.append(run_case(tid, text, exp))
        live.dataframe([{k: r[k] for k in COLUMNS} for r in rows], column_config=COLUMN_CONFIG, hide_index=True, width="stretch")
    progress.progress(1.0, text="Дууслаа")
    live.empty()
    run = {"at": datetime.now().strftime("%Y-%m-%d %H:%M"), "model": f"{provider()} / {model_name()}", "rows": rows}
    db.set_setting("last_test_run", json.dumps(run, ensure_ascii=False))
    db.audit("test-run", f"{run['model']}: {sum(r['Зөв'] for r in rows)}/{len(rows)} зөв")

# ---------- Сүүлийн үр дүн ----------
last = db.get_setting("last_test_run")
if last:
    run = json.loads(last)
    st.markdown("#### Сүүлийн ажиллагааны үр дүн")
    show_results(run["rows"], f"{run['at']} — {run['model']}")
else:
    st.info("Тест хараахан ажиллуулаагүй байна.")
