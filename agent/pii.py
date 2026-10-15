"""Хувийн мэдээллийг гадны AI руу илгээх, хадгалахаас өмнө нууцлана.

Дараалал: имэйл → регистр → +976 утас → данс/карт → 8 оронтой утас.
"""
import re

_CYR = "А-ЯЁӨҮа-яёөү"
RULES: list[tuple[str, re.Pattern]] = [
    ("EMAIL", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    # Регистр: 2 кирилл (эсвэл латин) үсэг + 8 оронтой тоо, жишээ УБ02210345 / UB02210345
    ("REGISTER", re.compile(rf"(?<![A-Za-z{_CYR}])[{_CYR}A-Za-z]{{2}}\s?\d{{8}}(?!\d)")),
    # Олон улсын форматтай утас (+976) — данс гэж андуурахаас өмнө
    ("PHONE", re.compile(r"\+?976[ -]?[5-9]\d{3}[ -]?\d{4}(?!\d)")),
    # Данс, карт: 9-19 оронтой тоо (зай, зураастай ч байж болно)
    ("ACCOUNT", re.compile(r"(?<!\d)\d(?:[ -]?\d){8,18}(?!\d)")),
    # Утас: 8 оронтой (5-9-өөр эхэлсэн), 4-4 хуваасан ч байж болно
    ("PHONE", re.compile(r"(?<!\d)[5-9]\d{3}[ -]?\d{4}(?!\d)")),
]


def mask_pii(text: str) -> tuple[str, list[str]]:
    """Нууцалсан текст ба олдсон шошгууд ("PHONE_1") — жинхэнэ утгыг хэзээ ч буцаахгүй."""
    found: list[str] = []
    counters: dict[str, int] = {}

    for label, pattern in RULES:
        def repl(_m: re.Match, label: str = label) -> str:
            counters[label] = counters.get(label, 0) + 1
            tag = f"[{label}_{counters[label]}]"
            found.append(tag)
            return tag

        text = pattern.sub(repl, text)
    return text, found
