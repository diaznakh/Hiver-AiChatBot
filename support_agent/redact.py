from __future__ import annotations

import re

EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
PHONE = re.compile(r"(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)")
ORDER = re.compile(
    r"\b(?:order|account|tracking)[\s#:=-]*(?=[A-Z0-9-]*\d)[A-Z0-9-]{6,}\b",
    re.I,
)
HANDLE = re.compile(r"(?<!\w)@[A-Za-z0-9_]{2,15}\b")


def redact_text(text: str) -> str:
    text = EMAIL.sub("[EMAIL]", text)
    text = PHONE.sub("[PHONE]", text)
    text = ORDER.sub(lambda m: m.group(0).split()[0] + " [IDENTIFIER]", text)
    return HANDLE.sub("[HANDLE]", text)
