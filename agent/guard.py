"""Prompt injection илрүүлэх детерминистик давхарга. LLM-ийн дүгнэлтээс үл хамааран ажиллана.

Кирилл, латин үсгээр бичсэн монгол болон англи хэлийг хамарна.
"""
import re

_I = re.IGNORECASE
PATTERNS: list[tuple[str, re.Pattern]] = [
    ("ignore-instructions-mn", re.compile(r"(өмнөх|дээрх|бүх|бусад).{0,25}(заава?р|дүр[эм]|тохиргоо).{0,25}(үл\s*тоо|мартаа?|орхи|хая|бүү\s*дага|хүчингүй)", _I)),
    ("ignore-instructions-latin", re.compile(r"(umnu?h|deerh|buh).{0,25}(zaava?r|durem|durm).{0,25}(ul\s*too|marta|orhi|haya)", _I)),
    ("ignore-instructions-en", re.compile(r"(ignore|disregard|forget|override|bypass).{0,30}(previous|prior|above|earlier|all|your|system).{0,20}(instructions?|rules?|prompts?|polic(y|ies)|guardrails?)", _I)),
    ("role-override-mn", re.compile(r"(чи|та)\s+(одоо(ноос)?|бол)\s+.{0,30}(админ|хөгжүүлэгч|root|хязгааргүй|хамгаалалтгүй)", _I)),
    ("role-override-latin", re.compile(r"\bchi\s+odoo\b.{0,30}(admin|administrator|system)", _I)),
    ("role-override-en", re.compile(r"\b(you are now|act as|pretend (to be|you are)|from now on you|developer mode|jailbreak|DAN mode)\b", _I)),
    ("prompt-exfiltration", re.compile(r"(system\s*prompt|системийн\s*(заавар|prompt)|your\s+instructions|зааврыг?аа\s+(харуул|хэл|гарга))", _I)),
    ("forced-output", re.compile(r"(гэж\s+хариул(аарай|(?![а-яёөү]))|reply\s+(only\s+)?with|respond\s+with\s+[\"“']|say\s+[\"“']?(success|done))", _I)),
    # Дангаараа injection биш (эрхийн хүсэлт байж болно) — бусадтай хамт л тооцно
    ("privileged-group", re.compile(r"\b(domain\s*admins?|enterprise\s*admins?|super\s*admin|global\s*admin)\b", _I)),
]


def detect_injection(text: str) -> tuple[bool, list[str]]:
    matches = [name for name, p in PATTERNS if p.search(text)]
    detected = any(m != "privileged-group" for m in matches)
    return detected, matches
