"""Даалгаврын 7-р хэсгийн 20 тест мессежийг агентаар ажиллуулж, хүлээгдэж буй үр дүнтэй харьцуулна.

Ажиллуулах:  python -m scripts.run_tests
Үр дүн:      test-results.md (тайланд хуулж оруулна)
Тэмдэглэл:   үндсэн DB-г бохирдуулахгүйн тулд data/test-run.db гэсэн тусдаа SQLite файл ашиглана.
Вэб дээр:    "Тест (20 мессеж)" хуудаснаас мөн ажиллуулж болно.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from agent import db
from agent.classify import model_name, provider
from agent.config import setting
from agent.testsuite import TESTS, run_case, to_markdown

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    # Pipe/background-д ажиллуулахад ч мөр бүр шууд харагдана
    sys.stdout.reconfigure(line_buffering=True)
    parser = argparse.ArgumentParser()
    # Gemini үнэгүй багц: минутад 5 хүсэлт → ~13 секунд тутам
    parser.add_argument("--delay", type=float, default=None, help="Мессеж хоорондын хүлээлт (сек)")
    args = parser.parse_args()
    key = "GEMINI_API_KEY" if provider() == "gemini" else "ANTHROPIC_API_KEY"
    if not setting(key):
        raise SystemExit(f"{key} тохируулаагүй байна (.streamlit/secrets.toml эсвэл орчны хувьсагч)")
    delay = args.delay if args.delay is not None else (13 if provider() == "gemini" else 0)
    print(f"LLM: {provider()} / {model_name()}, хүлээлт {delay}с\n")
    if db.backend() == "sqlite":
        db.SQLITE_PATH = ROOT / "data" / "test-run.db"
        db.SQLITE_PATH.unlink(missing_ok=True)

    rows = []
    for i, (tid, text, exp) in enumerate(TESTS):
        if i and delay:
            time.sleep(delay)
        row = run_case(tid, text, exp)
        rows.append(row)
        print(f"{tid} {row['Үнэлгээ']}  [{row['Ангилал']} / {row['Эрэмбэ']} / {row['Шийдвэр']} / {row['Баг']}]")

    (ROOT / "test-results.md").write_text(to_markdown(rows, f"{provider()} / {model_name()}"), encoding="utf-8")
    ok = sum(r["Зөв"] for r in rows)
    print(f"\nНарийвчлал: {ok}/{len(rows)} ({round(ok / len(rows) * 100)}%) → test-results.md")


if __name__ == "__main__":
    main()
