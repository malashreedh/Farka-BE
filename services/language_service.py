import re


def detect_language(text: str) -> str:
    """
    Detect language from user text.
    If more than 2 Nepali unicode characters found -> return "ne", else "en".
    Nepali Devanagari unicode range: \\u0900-\\u097F
    """
    nepali_chars = re.findall(r'[\u0900-\u097F]', text)
    if len(nepali_chars) > 2:
        return "ne"
    return "en"


def get_language_instruction(lang: str) -> str:
    """Return LLM instruction string for the given language."""
    if lang == "ne":
        return "You MUST respond entirely in Nepali (Devanagari script). Do not use English."
    return "Respond in clear, simple English."
