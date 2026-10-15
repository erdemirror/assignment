"""Эрэмбийн матриц ба SLA хугацаа (даалгаврын 2-р хэсэг)."""
from datetime import datetime, timedelta

# [нөлөө][яаралтай байдал]
MATRIX = {
    "Өндөр": {"Өндөр": "P1", "Дунд": "P2", "Бага": "P3"},
    "Дунд": {"Өндөр": "P2", "Дунд": "P3", "Бага": "P3"},
    "Бага": {"Өндөр": "P3", "Дунд": "P3", "Бага": "P4"},
}

SLA = {
    "P1": {"response": "15 мин", "resolve": "4 цаг", "escalate": "Нэн даруй, 30 мин тутам шинэчлэл"},
    "P2": {"response": "30 мин", "resolve": "8 цаг", "escalate": "SLA-ийн 75% өнгөрөхөд"},
    "P3": {"response": "2 цаг", "resolve": "2 ажлын өдөр", "escalate": "SLA хэтэрсэн үед"},
    "P4": {"response": "4 цаг", "resolve": "5 ажлын өдөр", "escalate": "—"},
}


def priority_from(impact: str, urgency: str) -> str:
    return MATRIX[impact][urgency]


def _add_business_days(start: datetime, days: int) -> datetime:
    d = start
    while days > 0:
        d += timedelta(days=1)
        if d.weekday() < 5:
            days -= 1
    return d


def due_date(priority: str, start: datetime) -> datetime:
    """Таамаглал: P1/P2 нь 24/7 цагаар, P3/P4 нь ажлын өдрөөр тоологдоно (баярын өдөр тооцоогүй)."""
    if priority == "P1":
        return start + timedelta(hours=4)
    if priority == "P2":
        return start + timedelta(hours=8)
    if priority == "P3":
        return _add_business_days(start, 2)
    return _add_business_days(start, 5)
