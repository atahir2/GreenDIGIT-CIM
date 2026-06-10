import re
from typing import Tuple, Optional

_UNIT_PATTERNS = [
    (re.compile(r"^\s*(\d+(?:\.\d+)?)\s*%"), "percent"),
    (re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(?:mb|mib)\b", re.I), "mb"),
    (re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(?:gb|gib)\b", re.I), "gb"),
    (re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(?:w|watts)\b", re.I), "w"),
]

def extract_numeric_and_unit(text_or_number) -> Tuple[Optional[float], Optional[str]]:
    if isinstance(text_or_number, (int, float)):
        return float(text_or_number), None
    s = str(text_or_number).strip()
    for pat, unit in _UNIT_PATTERNS:
        m = pat.search(s)
        if m:
            return float(m.group(1)), unit
    # fallback: plain float
    try:
        return float(s), None
    except ValueError:
        return None, None
