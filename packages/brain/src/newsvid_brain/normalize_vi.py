from __future__ import annotations

import hashlib
import re
from pathlib import Path

import yaml
from pydantic import Field

from .models import StrictModel

NORMALIZER_VERSION = "vi-normalizer-v1"

_DIGITS = ("không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín")
_SCALES = ("", "nghìn", "triệu", "tỷ", "nghìn tỷ", "triệu tỷ")


class PronunciationConfig(StrictModel):
    version: int = 1
    acronyms: dict[str, str] = Field(default_factory=dict)
    currencies: dict[str, str] = Field(default_factory=dict)
    units: dict[str, str] = Field(default_factory=dict)
    replacements: dict[str, str] = Field(default_factory=dict)


def load_pronunciation(path: Path) -> PronunciationConfig:
    return PronunciationConfig.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")) or {})


def pronunciation_fingerprint(config: PronunciationConfig) -> str:
    payload = config.model_dump_json()
    return hashlib.sha256(f"{NORMALIZER_VERSION}:{payload}".encode("utf-8")).hexdigest()


def _under_hundred(value: int, *, leading: bool = False) -> str:
    if value < 10:
        return ("lẻ " if leading and value else "") + _DIGITS[value]
    tens, ones = divmod(value, 10)
    words = "mười" if tens == 1 else f"{_DIGITS[tens]} mươi"
    if ones == 0:
        return words
    if ones == 1 and tens > 1:
        tail = "mốt"
    elif ones == 5:
        tail = "lăm"
    else:
        tail = _DIGITS[ones]
    return f"{words} {tail}"


def _under_thousand(value: int, *, full: bool = False) -> str:
    hundreds, remainder = divmod(value, 100)
    if hundreds:
        head = f"{_DIGITS[hundreds]} trăm"
    elif full and remainder:
        head = "không trăm"
    else:
        head = ""
    if not remainder:
        return head or "không"
    tail = _under_hundred(remainder, leading=bool(head) and remainder < 10)
    return f"{head} {tail}".strip()


def integer_to_vi(value: int) -> str:
    if value == 0:
        return "không"
    if value < 0:
        return f"âm {integer_to_vi(-value)}"
    groups: list[int] = []
    remaining = value
    while remaining:
        groups.append(remaining % 1000)
        remaining //= 1000
    if len(groups) > len(_SCALES):
        return " ".join(_DIGITS[int(ch)] for ch in str(value))
    parts: list[str] = []
    highest = len(groups) - 1
    for index in range(highest, -1, -1):
        group = groups[index]
        if not group:
            continue
        spoken = _under_thousand(group, full=index < highest)
        scale = _SCALES[index]
        parts.append(f"{spoken} {scale}".strip())
    return " ".join(parts)


def _number_to_vi(raw: str) -> str:
    value = raw.strip()
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", value):
        return integer_to_vi(int(value.replace(".", "")))
    if re.fullmatch(r"\d{1,3}(?:,\d{3})+", value):
        return integer_to_vi(int(value.replace(",", "")))
    separator = "," if "," in value else "." if "." in value else None
    if separator:
        whole, fraction = value.split(separator, 1)
        return f"{integer_to_vi(int(whole))} phẩy {' '.join(_DIGITS[int(ch)] for ch in fraction)}"
    return integer_to_vi(int(value))


def _replace_dictionary(text: str, entries: dict[str, str]) -> str:
    for key in sorted(entries, key=len, reverse=True):
        pattern = rf"(?<![\w]){re.escape(key)}(?![\w])"
        text = re.sub(pattern, entries[key], text, flags=re.IGNORECASE)
    return text


def normalize_vi(text: str, config: PronunciationConfig) -> str:
    value = re.sub(r"\s+", " ", text).strip()
    value = _replace_dictionary(value, config.replacements)
    value = re.sub(
        r"(?<!\w)(?:ngày\s+)?(\d{1,2})[/-](\d{1,2})[/-](\d{4})(?!\d)",
        lambda m: f"ngày {integer_to_vi(int(m.group(1)))} tháng {integer_to_vi(int(m.group(2)))} năm {integer_to_vi(int(m.group(3)))}",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(r"\$\s*(\d(?:[\d.,]*\d)?)", lambda m: f"{_number_to_vi(m.group(1))} đô la Mỹ", value)
    value = re.sub(r"(\d(?:[\d.,]*\d)?)\s*%", lambda m: f"{_number_to_vi(m.group(1))} phần trăm", value)
    value = _replace_dictionary(value, config.acronyms)
    value = _replace_dictionary(value, config.currencies)
    value = _replace_dictionary(value, config.units)
    value = re.sub(r"(?<![\w])\d(?:[\d.,]*\d)?(?![\w])", lambda m: _number_to_vi(m.group(0)), value)
    return re.sub(r"\s+([,.;:!?])", r"\1", re.sub(r"\s+", " ", value)).strip()
