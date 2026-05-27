from __future__ import annotations

import re
from collections.abc import Iterable

MODULE_PATTERN = re.compile(r"(?<![A-Z0-9])M\d{3}(?![A-Z0-9])|^(?:DE|GR|FR|PH)(?=$|[\s_.-])", re.IGNORECASE)
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_patterns(patterns: Iterable[str]) -> list[str]:
    """

    Args:
        patterns (Iterable[str]): _description_

    Returns:
        list[str]: _description_
    """
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
    """

    Args:
        text (str): _description_

    Returns:
        list[str]: _description_
    """
    modules = []
    for match in MODULE_PATTERN.finditer(text):
        module_name = match.group(0).upper()
        if module_name not in modules:
            modules.append(module_name)
    return modules


def is_valid_email(value: str) -> bool:
    """

    Args:
        value (str): _description_

    Returns:
        bool: _description_
    """
    return EMAIL_PATTERN.fullmatch(value.strip()) is not None
