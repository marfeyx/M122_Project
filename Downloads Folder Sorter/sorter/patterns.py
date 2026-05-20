from __future__ import annotations

import re
from collections.abc import Iterable

MODULE_PATTERN = re.compile(r"M\d{3}|^(?:DE|GR|FR|PH)(?=$|[\s_.-])", re.IGNORECASE)
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_patterns(patterns: Iterable[str]) -> list[str]:
    normalized = []
    for pattern in patterns:
        pattern_as_text = str(pattern).strip()
        match = MODULE_PATTERN.fullmatch(pattern_as_text)
        if match is None:
            continue
        module_name = match.group(0).upper()
        if module_name not in normalized:
            normalized.append(module_name)
    normalized.sort()
    return normalized


def find_modules(text: str) -> list[str]:
    modules = []
    for match in MODULE_PATTERN.finditer(text):
        module_name = match.group(0).upper()
        if module_name not in modules:
            modules.append(module_name)
    return modules


def is_valid_email(value: str) -> bool:
    return EMAIL_PATTERN.fullmatch(value.strip()) is not None
