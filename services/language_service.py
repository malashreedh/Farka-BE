import re


NEPALI_PATTERN = re.compile(r"[\u0900-\u097F]")


def detect_language(text: str) -> str:
    matches = NEPALI_PATTERN.findall(text or "")
    return "ne" if len(matches) > 2 else "en"


def get_language_instruction(lang: str) -> str:
    if lang == "ne":
        return "You MUST respond entirely in Nepali (Devanagari script). Do not use English."
    return "Respond in clear, simple English."
