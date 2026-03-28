from __future__ import annotations

from typing import Any

from models import LanguageEnum, PathEnum, SavingsRangeEnum, TradeCategoryEnum


ENUM_FIELDS = {
    "path": {item.value for item in PathEnum},
    "trade_category": {item.value for item in TradeCategoryEnum},
    "language_pref": {item.value for item in LanguageEnum},
    "savings_range": {item.value for item in SavingsRangeEnum},
}

MEANINGFUL_FIELDS = {
    "name",
    "phone",
    "current_location",
    "years_experience",
    "skills",
    "district_target",
    "has_savings",
    "savings_range",
}


def sanitize_profile_updates(payload: dict[str, Any]) -> dict[str, Any]:
    clean: dict[str, Any] = {}
    for key, value in payload.items():
        if value is None:
            continue

        if key in ENUM_FIELDS:
            if key == "path" and value == "undecided":
                continue
            if key == "trade_category" and value == "other":
                continue
            if value in ENUM_FIELDS[key]:
                clean[key] = value
            continue

        if key == "skills":
            if isinstance(value, list):
                clean[key] = [str(item).strip() for item in value if str(item).strip()]
            elif isinstance(value, str) and value.strip():
                clean[key] = [part.strip() for part in value.split(",") if part.strip()]
            continue

        clean[key] = value

    return clean


def has_meaningful_profile_data(payload: dict[str, Any]) -> bool:
    for key, value in payload.items():
        if key in {"path", "trade_category"} and value:
            return True
        if key in MEANINGFUL_FIELDS and value not in (None, [], ""):
            return True
    return False
