"""Аюулгүй байдлын болон бизнесийн хатуу дүрмүүд. LLM буруу дүгнэлт гаргасан ч эдгээр нь давамгайлна."""
from __future__ import annotations

import re

from .classify import LlmRequest
from .kb import ALLOWED_URLS, KB_IDS
from .models import L1, SEC, SYS
from .priority import priority_from

COMPROMISE_RE = re.compile(
    r"(фишинг|phishing|сэжигтэй\s+(линк|имэйл|холбоос)|ransom|шифрлэгд|encrypted|bitcoin|\bBTC\b|malware|вирус|virus|"
    r"нууц\s+үгээ?\s+оруулчих|hacked|хакдсан|хакерд)",
    re.IGNORECASE,
)

REPLY_INJECTION = (
    "Таны мессежид агентын ажиллах журмыг өөрчлөх оролдлого илэрсэн тул хүсэлтийг гүйцэтгэх боломжгүй. "
    "Агент эрх олгох, бүлэгт нэмэх, нууц үг шинэчлэх үйлдлийг хийдэггүй. Хэрэв танд бодит эрхийн хэрэгцээ байгаа бол "
    "шууд удирдлага болон системийн эзэмшигч хэлтсийн зөвшөөрөлтэйгээр эрхийн хүсэлт гаргана уу (KB-06). "
    "Энэ оролдлогыг Мэдээллийн аюулгүй байдлын багт бүртгэж мэдэгдлээ."
)
REPLY_COMPROMISE = (
    "Таны хүсэлтийг яаралтай (P1) гэж бүртгээд Мэдээллийн аюулгүй байдлын багт нэн даруй шилжүүллээ. "
    "Тэд тантай удахгүй холбогдоно. Тэр хүртэл:\n"
    "• Сэжигтэй имэйлийг УСТГАХГҮЙ байна уу (шинжилгээнд хэрэгтэй).\n"
    "• Линк дээр дахин бүү дарна уу.\n"
    "• Компьютерийг сүлжээнээс салгахгүйгээр унтраахгүй байна уу.\n"
    "Бид таны нууц үгийг хэзээ ч асуухгүй — нууц үг асуусан мессеж, дуудлагад бүү хариулаарай. (KB-09)"
)
REPLY_OTHERS_PASSWORD = (
    "Уучлаарай, бусдын нууц үгийг шинэчлэх эсвэл гуравдагч этгээдэд өгөх боломжгүй (KB-01). "
    "Тухайн ажилтан өөрөө https://reset.example-netcap.mn (Self-Service Password Reset) хаягаар орж, "
    "бүртгэлтэй утасны дугаарт ирсэн кодоор шинэчилнэ. SSPR-д бүртгэлгүй бол Service Desk видео дуудлагаар "
    "иргэний үнэмлэхийг нь шалгаж түр нууц үг олгоно."
)
REPLY_BULK_DATA = (
    "Ажилтны жагсаалт, утас, имэйл зэрэг хувийн мэдээллийг энэ сувгаар гаргах боломжгүй. "
    "Аудитын зорилгоор мэдээлэл шаардлагатай бол албан ёсны хүсэлтээ удирдлагын зөвшөөрөлтэйгээр гаргана уу. "
    "Хүсэлтийг Мэдээллийн аюулгүй байдлын багт бүртгэж мэдэгдлээ."
)
REPLY_OFFBOARDING = (
    "Ажлаас гарсан ажилтны эрхийг хаах хүсэлтийг хүлээн авлаа. KB-06-ийн дагуу HR-ын баталсан тойрох хуудас "
    "ирсэн өдөр эрхийг хаадаг тул Системийн багт өнөөдөр гүйцэтгүүлэхээр шилжүүллээ. Хавсралтын жинхэнэ эсэхийг "
    "ажилтан шалгасны дараа хаалт хийгдэнэ."
)
REPLY_ACCESS_APPROVED = (
    "Таны эрхийн хүсэлтийг бүртгэлээ. Шаардлагатай зөвшөөрлүүд дурдагдсан тул Системийн баг зөвшөөрлийг "
    "баталгаажуулсны дараа гүйцэтгэнэ (KB-06). Агент өөрөө эрх олгодоггүй."
)


def _status_for(decision: str, team: str) -> str:
    return {
        "Хариулах": "Шийдвэрлэсэн",
        "Татгалзах": "Татгалзсан",
        "Тодруулах": "Тодруулга хүлээж буй",
        "Шилжүүлэх": "Шинэ" if team == L1 else "L2-т шилжсэн",
    }[decision]


def _default_l2_note(r: dict, masked_text: str) -> str:
    lines = [
        f"Хүсэлт: {r['summary']}",
        f"Төрөл/эрэмбэ: {r['type']} / {r['priority'] or '—'}",
        f"Байршил: {r['location']}",
        f"Хүсэлт гаргагч: {r['requester']}" if r["requester"] else None,
        f"Хугацаа: {r['time_info']}" if r["time_info"] else None,
        f'Эх мессеж (нууцалсан): "{masked_text[:300]}"',
    ]
    return "\n".join(line for line in lines if line)


def _strip_unknown_urls(reply: str, flags: list[str]) -> str:
    def repl(m: re.Match) -> str:
        if m.group(0).rstrip(".,") in ALLOWED_URLS:
            return m.group(0)
        flags.append("unknown-url-removed")
        return "[хаяг устгав]"

    return re.sub(r"https?://[^\s)]+", repl, reply)


def apply_policy(llm: LlmRequest, injection: bool, guard_matches: list[str], masked_text: str) -> dict:
    """LLM-ийн гаралт дээр хатуу дүрмүүдийг хэрэгжүүлээд тикетийн талбаруудыг буцаана."""
    r = llm.model_dump(include={
        "summary", "type", "impact", "urgency", "team", "service", "decision", "requester",
        "affected_user", "location", "time_info", "reply", "l2_note",
    })
    r.update(kb_ids=[k for k in llm.kb_ids if k in KB_IDS], priority=None, status="Шинэ", flags=[], policy_notes=[])
    if any(k not in KB_IDS for k in llm.kb_ids):
        r["flags"].append("invalid-kb-removed")

    def override(note: str, **patch) -> None:
        r.update(patch)
        r["policy_notes"].append(note)

    # 1) Prompt injection — бусад бүх дүрмээс өмнө
    if injection or llm.injection_attempt:
        r["flags"].append("prompt-injection")
        override(
            "Prompt injection илэрсэн тул татгалзаж, аюулгүй байдлын багт мэдэгдэв",
            type="Security", team=SEC, service="security", decision="Татгалзах", kb_ids=[],
            impact="Дунд", urgency="Өндөр", reply=REPLY_INJECTION,
            l2_note=(
                f"Prompt injection оролдлого илэрлээ (дүрэм: {', '.join(guard_matches) or 'LLM'}). Ямар ч үйлдэл хийгээгүй. "
                f'Хүсэлт гаргагчийг шалгах шаардлагатай.\nМессеж (нууцалсан): "{masked_text[:300]}"'
            ),
        )
        return _finalize(r, masked_text)

    # 2) Фишинг / бүртгэл алдагдсан / malware — KB-09
    if llm.compromise_suspected or llm.user_entered_credentials or (COMPROMISE_RE.search(masked_text) and llm.type == "Security"):
        r["flags"].append("security-compromise")
        override(
            "Бүртгэл алдагдсан/malware сэжигтэй тул KB-09-ийн дагуу P1, аюулгүй байдлын багт шилжүүлэв",
            type="Security", team=SEC, service="security", decision="Шилжүүлэх", kb_ids=["KB-09"],
            impact="Өндөр", urgency="Өндөр", reply=REPLY_COMPROMISE,
        )
        return _finalize(r, masked_text)

    # 3) Бусдын нууц үг — хэзээ ч өгөхгүй
    if llm.credential_for_other_person:
        r["flags"].append("third-party-credential")
        override(
            "Бусдын нууц үг хүссэн тул татгалзав (KB-01)",
            type="Security", team=SEC, service="security", decision="Татгалзах", kb_ids=["KB-01"],
            impact="Бага", urgency="Дунд", reply=REPLY_OTHERS_PASSWORD,
        )
        return _finalize(r, masked_text)

    # 4) Олноор нь хувийн мэдээлэл хүссэн
    if llm.asks_for_bulk_personal_data:
        r["flags"].append("data-exfiltration-attempt")
        override(
            "Хувийн мэдээлэл задруулах хүсэлт тул татгалзаж, аюулгүй байдлын багт мэдэгдэв",
            type="Security", team=SEC, service="security", decision="Татгалзах", kb_ids=[],
            impact="Дунд", urgency="Дунд", reply=REPLY_BULK_DATA,
            l2_note=(
                f"Хувийн мэдээллийн жагсаалт хүссэн хүсэлт (нийгмийн инженерчлэл байж болзошгүй). "
                f"Хүсэлт гаргагч: {llm.requester or 'тодорхойгүй'}. Мэдээлэл гаргаагүй.\n"
                f'Мессеж (нууцалсан): "{masked_text[:300]}"'
            ),
        )
        return _finalize(r, masked_text)

    # 5) IT-тэй хамааралгүй
    if r["type"] == "Хамааралгүй" or r["team"] == "Хамааралгүй":
        r.update(type="Хамааралгүй", team="Хамааралгүй", kb_ids=[])
        if r["decision"] != "Тодруулах":
            r["decision"] = "Татгалзах"
        return _finalize(r, masked_text)

    # 6) Эрхийн хүсэлт — KB-06, агент хэзээ ч өөрөө эрх олгохгүй
    if llm.is_access_change or r["type"] == "Access":
        r.update(type="Access", service="access", team=SYS, kb_ids=sorted(set(r["kb_ids"]) | {"KB-06"}))
        if llm.is_offboarding and llm.has_hr_clearance:
            override(
                "Offboarding: HR тойрох хуудас ирсэн тул өнөөдөр хаахаар Системийн багт шилжүүлэв (KB-06)",
                decision="Шилжүүлэх", reply=REPLY_OFFBOARDING, status="L2-т шилжсэн", impact="Бага", urgency="Өндөр",
            )
            return _finalize(r, masked_text, keep_status=True)

        missing = []
        if llm.is_offboarding:
            missing.append("HR-ын баталсан тойрох хуудас")
        else:
            if not llm.has_manager_approval:
                missing.append("шууд удирдлагын зөвшөөрөл")
            if not llm.has_owner_approval and not llm.requester_owns_resource:
                missing.append("өгөгдөл/системийн эзэмшигч хэлтсийн зөвшөөрөл")
        if missing:
            m = ", ".join(missing)
            override(
                f'Эрхийн хүсэлт: дутуу зөвшөөрөл ({m}) → "Зөвшөөрөл хүлээж буй"',
                decision="Шилжүүлэх", status="Зөвшөөрөл хүлээж буй", impact="Бага",
                urgency="Дунд" if r["urgency"] == "Өндөр" else r["urgency"],
                reply=(
                    "Таны эрхийн хүсэлтийг бүртгэлээ. KB-06 журмын дагуу эрхийн бүх хүсэлт (1) шууд удирдлагын болон "
                    f"(2) өгөгдөл/системийн эзэмшигч хэлтсийн зөвшөөрөлтэй байх ёстой. Одоогоор дутуу: {m}. "
                    'Хүсэлтийг "Зөвшөөрөл хүлээж буй" төлөвт орууллаа — зөвшөөрөл ирмэгц Системийн баг гүйцэтгэнэ. '
                    "Агент өөрөө эрх олгодоггүйг анхаарна уу."
                ),
            )
            return _finalize(r, masked_text, keep_status=True)

        override(
            "Эрхийн хүсэлт: зөвшөөрөл дурдагдсан, хүн баталгаажуулахаар Системийн багт шилжүүлэв",
            decision="Шилжүүлэх", reply=REPLY_ACCESS_APPROVED,
        )
        return _finalize(r, masked_text)

    # 7) KB-гүйгээр "Хариулах" боломжгүй — мэдээлэл зохиохгүй
    if r["decision"] == "Хариулах" and not r["kb_ids"]:
        override(
            "KB иш байхгүй тул Хариулах → Шилжүүлэх",
            decision="Шилжүүлэх",
            reply=f"Таны хүсэлтийг бүртгэлээ. Мэдлэгийн санд энэ асуудлын бэлэн заавар байхгүй тул {r['team']}-д шилжүүллээ, тэд тантай холбогдоно.",
        )

    return _finalize(r, masked_text)


def _finalize(r: dict, masked_text: str, keep_status: bool = False) -> dict:
    r["priority"] = None if r["type"] == "Хамааралгүй" else priority_from(r["impact"], r["urgency"])

    # P1 бол заавал хүнд шилжүүлнэ
    if r["priority"] == "P1" and r["decision"] == "Хариулах":
        r["decision"] = "Шилжүүлэх"
        r["policy_notes"].append("P1 тул хүний оролцоотойгоор Шилжүүлэх")
    if r["decision"] == "Шилжүүлэх" and not r["l2_note"]:
        r["l2_note"] = _default_l2_note(r, masked_text)
    if r["decision"] != "Шилжүүлэх" and r["type"] != "Security":
        r["l2_note"] = None
    if not keep_status:
        r["status"] = _status_for(r["decision"], r["team"])
    r["reply"] = _strip_unknown_urls(r["reply"], r["flags"])
    return r


def should_notify(priority: str | None, ticket_type: str) -> bool:
    return priority == "P1" or ticket_type == "Security"
