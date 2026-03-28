from __future__ import annotations

import json
import os
import re
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from models import ChatSession, Profile
from schemas import ChecklistItem
from services.language_service import get_language_instruction
from services.workflow_config import DISTRICT_CHOICES, PATH_CHOICES, SAVINGS_CHOICES, SKILL_TAGS

load_dotenv()

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
FALLBACK_MODELS = [OPENAI_MODEL, "gpt-4o-mini", "gpt-4o"]
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None

TRADE_KEYWORDS = {
    "construction": ["construction", "builder", "mason", "site", "plumbing", "electric", "scaffold", "निर्माण", "मिस्त्री"],
    "hospitality": ["hotel", "restaurant", "hospitality", "kitchen", "housekeeping", "guest", "hotel operations", "होटल", "रेस्टुरेन्ट"],
    "manufacturing": ["factory", "manufacturing", "welding", "assembly", "machine", "फ्याक्ट्री", "मेसिन"],
    "agriculture": ["farm", "agriculture", "crop", "livestock", "harvest", "कृषि", "खेती", "पशुपालन"],
    "domestic": ["housemaid", "domestic", "caregiver", "childcare", "elder care", "home", "घरेलु", "हेरचाह"],
    "transport": ["driver", "transport", "logistics", "cargo", "vehicle", "ड्राइभर", "यातायात"],
    "tech": ["tech", "it", "developer", "computer", "digital", "support", "प्रविधि", "कम्प्युटर"],
}

DISTRICTS = ["Kathmandu", "Lalitpur", "Bhaktapur", "Pokhara", "Chitwan", "Biratnagar", "Butwal"]
SAVINGS_MAP = {
    "under_5L": ["under 5", "under_5l", "below 5", "less than 5", "5 लाखभन्दा कम"],
    "5L_to_20L": ["5l_to_20l", "5 to 20", "5-20", "between 5 and 20", "५ देखि २०"],
    "20L_to_50L": ["20l_to_50l", "20 to 50", "20-50", "between 20 and 50", "२० देखि ५०"],
    "above_50L": ["above 50", "more than 50", "over 50", "above_50l", "५० लाखभन्दा माथि"],
}

EXTRACT_PATTERN = re.compile(r"<extract>(.*?)</extract>", re.DOTALL)


def get_welcome_message(language: str) -> str:
    if language == "ne":
        return (
            "नमस्ते! म FARKA हुँ। म विदेशबाट फर्किन चाहने नेपालीहरूलाई "
            "नेपालमा जागिर वा व्यवसायको बाटो खोज्न मद्दत गर्छु। "
            "सुरु गरौं, अहिले तपाईं कहाँ हुनुहुन्छ?"
        )
    return (
        "Namaste! I'm FARKA. I help Nepali workers abroad see what is realistically possible back in Nepal, "
        "whether that means a job or a small business. First, where are you right now?"
    )


def process_message(session: ChatSession, user_message: str) -> dict[str, Any]:
    stage = _enum_value(session.workflow_stage)
    language = _enum_value(session.language) or "en"

    if not client:
        return _fallback_process(session, user_message)

    last_messages = json.dumps((session.messages or [])[-4:], ensure_ascii=False)
    prompt = f"""
You are FARKA, a friendly and practical return-migration advisor for Nepali workers abroad.
{get_language_instruction(language)}
Current workflow stage: {stage}
Conversation so far: {last_messages}

Behavior rules:
- Sound warm, practical, and trustworthy.
- Ask only the next most useful question.
- Keep replies concise and natural, like a real product assistant.
- Use Nepal-specific context when helpful.
- For job seekers, keep skill tags in English internally.

Stage instructions:
- language_set: confirm their location and ask what type of work they did abroad.
- collecting_basics: identify name if provided, current_location, and trade_category. Then ask years of experience.
- collecting_experience: identify years_experience, then ask whether they want a job or want to start a business in Nepal.
- path_decision: set path to job_seeker or business_starter.
- collecting_skills: identify skills from the user's answer and confirm you are moving to job matching.
- collecting_business_details: identify district_target, savings_range, has_savings, and business idea text. Then confirm you are generating a checklist.

At the very end, output one JSON block inside <extract></extract>.
Use this exact shape:
<extract>{{
  "name": null,
  "current_location": null,
  "trade_category": null,
  "years_experience": null,
  "path": null,
  "skills": [],
  "district_target": null,
  "savings_range": null,
  "has_savings": null,
  "next_stage": "{stage}",
  "redirect": null
}}</extract>

Allowed enum values:
- trade_category: construction, hospitality, manufacturing, agriculture, domestic, transport, tech, other
- path: job_seeker, business_starter, undecided
- savings_range: under_5L, 5L_to_20L, 20L_to_50L, above_50L
- redirect: null, jobs, checklist
""".strip()

    for model in FALLBACK_MODELS:
        try:
            response = client.chat.completions.create(
                model=model,
                temperature=0.25,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user_message},
                ],
            )
            content = response.choices[0].message.content or ""
            reply, extracted = _parse_extract(content)
            clean = _normalize_extracted_data(extracted, session)
            if not reply:
                reply = _fallback_process(session, user_message)["reply"]
            return {
                "reply": reply,
                "extracted_data": clean["fields"],
                "next_stage": clean["next_stage"],
                "redirect": clean["redirect"],
            }
        except Exception:
            continue

    return _fallback_process(session, user_message)


def generate_checklist(profile: Profile) -> dict[str, Any]:
    language = _enum_value(profile.language_pref) or "en"
    trade = _enum_value(profile.trade_category) or "other"
    district = profile.district_target or "Kathmandu"
    savings = _enum_value(profile.savings_range) or "under_5L"
    business_idea = ", ".join(profile.skills or []) or trade

    if not client:
        items = _generic_checklist(trade, district)
        return {"checklist_items": items, "raw_ai_output": json.dumps(items, ensure_ascii=False)}

    system_prompt = f"""
You are a Nepal-focused small business advisor.
{get_language_instruction(language)}
Generate a grounded 8-week launch checklist for a returning Nepali migrant worker.
Be realistic, specific, and action-oriented.
Output ONLY valid JSON.
""".strip()

    user_prompt = (
        f"Profile: trade={trade}, district={district}, savings={savings}, business idea={business_idea}. "
        "Return a JSON array only. Each item must be {category: str, week: int, task: str, done: false}. "
        "Use categories from Legal & Registration, Finance & Loans, Location & Equipment, Marketing, Operations."
    )

    for model in FALLBACK_MODELS:
        try:
            response = client.chat.completions.create(
                model=model,
                temperature=0.2,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            raw = response.choices[0].message.content or "[]"
            items = _validate_checklist_items(json.loads(raw))
            if not items:
                raise ValueError("Empty checklist")
            return {"checklist_items": items, "raw_ai_output": raw}
        except Exception:
            continue

    items = _generic_checklist(trade, district)
    return {"checklist_items": items, "raw_ai_output": json.dumps(items, ensure_ascii=False)}


def _fallback_process(session: ChatSession, user_message: str) -> dict[str, Any]:
    stage = _enum_value(session.workflow_stage)
    language = _enum_value(session.language) or "en"
    text = user_message.strip()
    lower = text.lower()
    extracted: dict[str, Any] = {}
    next_stage = stage
    redirect = None

    if stage == "language_set":
        extracted["current_location"] = text
        next_stage = "collecting_basics"
        reply = _respond(
            language,
            "Thank you. Which work area best fits what you did abroad? For example: construction, hospitality, transport, agriculture, manufacturing, domestic work, or tech.",
            "धन्यवाद। विदेशमा तपाईंले गरेको काम कुन क्षेत्रमा पर्छ? जस्तै निर्माण, हस्पिटालिटी, यातायात, कृषि, उत्पादन, घरेलु काम, वा टेक।",
        )
    elif stage == "collecting_basics":
        extracted.update(_extract_basics(text))
        next_stage = "collecting_experience"
        reply = _respond(
            language,
            "How many years of experience do you have in that work?",
            "त्यो काममा तपाईंको कति वर्षको अनुभव छ?",
        )
    elif stage == "collecting_experience":
        extracted["years_experience"] = _extract_years(lower)
        next_stage = "path_decision"
        reply = _respond(
            language,
            "When you return to Nepal, would you prefer a job or your own business?",
            "नेपाल फर्केपछि तपाईं जागिर चाहनुहुन्छ कि आफ्नै व्यवसाय?",
        )
    elif stage == "path_decision":
        extracted["path"] = "business_starter" if any(token in lower for token in ["business", "व्यवसाय"]) else "job_seeker"
        if extracted["path"] == "job_seeker":
            next_stage = "collecting_skills"
            trade = _infer_trade_from_session(session.messages)
            suggestions = ", ".join(SKILL_TAGS.get(trade, SKILL_TAGS["construction"])[:6])
            reply = _respond(
                language,
                f"Great. Which of these skills match you: {suggestions}? You can add your own too.",
                f"राम्रो। यी सीपमध्ये कुन-कुन तपाईंलाई मिल्छ: {suggestions}? आफ्नै सीप पनि थप्न सक्नुहुन्छ।",
            )
        else:
            next_stage = "collecting_business_details"
            districts = ", ".join(DISTRICT_CHOICES[:4])
            reply = _respond(
                language,
                f"Great. Which district do you want to return to, how much do you have in savings, and what business idea do you have? Common districts: {districts}.",
                f"राम्रो। तपाईं कुन जिल्लामा फर्किन चाहनुहुन्छ, कति बचत छ, र कस्तो व्यवसायको योजना छ? सामान्य जिल्ला उदाहरण: {districts}।",
            )
    elif stage == "collecting_skills":
        extracted["skills"] = _extract_skills(text, _infer_trade_from_session(session.messages))
        next_stage = "job_matching"
        redirect = "jobs"
        reply = _respond(
            language,
            "Your profile is ready. I am now matching you to jobs in Nepal.",
            "तपाईंको प्रोफाइल तयार भयो। अब नेपालमा तपाईंलाई मिल्ने जागिर खोज्दैछु।",
        )
    elif stage == "collecting_business_details":
        extracted.update(_extract_business_details(text))
        next_stage = "checklist_generated"
        redirect = "checklist"
        reply = _respond(
            language,
            "Your profile is ready. I am now preparing your business roadmap.",
            "तपाईंको प्रोफाइल तयार भयो। अब तपाईंको व्यवसाय रोडम्याप तयार गर्दैछु।",
        )
    else:
        reply = _respond(language, "Thanks. Tell me a bit more.", "धन्यवाद। अलि थप जानकारी दिनुस्।")

    return {"reply": reply, "extracted_data": extracted, "next_stage": next_stage, "redirect": redirect}


def _parse_extract(response_text: str) -> tuple[str, dict[str, Any]]:
    match = EXTRACT_PATTERN.search(response_text or "")
    if not match:
        return response_text.strip(), {}
    extract_text = match.group(1).strip()
    reply = EXTRACT_PATTERN.sub("", response_text).strip()
    try:
        return reply, json.loads(extract_text)
    except Exception:
        return reply, {}


def _normalize_extracted_data(extracted: dict[str, Any], session: ChatSession) -> dict[str, Any]:
    stage = _enum_value(session.workflow_stage)
    inferred_years = _infer_years_from_session(session.messages)
    fields = {
        "name": extracted.get("name"),
        "current_location": extracted.get("current_location"),
        "trade_category": _clean_trade(extracted.get("trade_category")) or _infer_trade_from_session(session.messages),
        "years_experience": _coerce_years(extracted.get("years_experience")) or inferred_years,
        "path": extracted.get("path") if extracted.get("path") in PATH_CHOICES or extracted.get("path") == "undecided" else None,
        "skills": _coerce_skills(extracted.get("skills")),
        "district_target": _clean_district(extracted.get("district_target")),
        "savings_range": extracted.get("savings_range") if extracted.get("savings_range") in SAVINGS_CHOICES else None,
        "has_savings": _coerce_bool(extracted.get("has_savings")),
    }

    next_stage = extracted.get("next_stage") or stage
    redirect = extracted.get("redirect")

    if stage == "language_set":
        next_stage = "collecting_basics"
    elif stage == "collecting_basics":
        next_stage = "path_decision" if fields["trade_category"] and fields["years_experience"] else "collecting_experience"
    elif stage == "collecting_experience":
        if fields["path"] == "job_seeker":
            next_stage = "collecting_skills"
        elif fields["path"] == "business_starter":
            next_stage = "collecting_business_details"
        else:
            next_stage = "path_decision"
    elif stage == "path_decision":
        if fields["path"] == "job_seeker":
            next_stage = "collecting_skills"
        elif fields["path"] == "business_starter":
            next_stage = "collecting_business_details"
    elif stage == "collecting_skills":
        next_stage = "job_matching"
        redirect = "jobs"
    elif stage == "collecting_business_details":
        next_stage = "checklist_generated"
        redirect = "checklist"

    return {"fields": {k: v for k, v in fields.items() if v not in (None, [], "")}, "next_stage": next_stage, "redirect": redirect}


def _infer_trade(text: str) -> str:
    for trade, keywords in TRADE_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return trade
    return "other"


def _infer_trade_from_session(messages: list[dict[str, Any]] | None) -> str:
    history = " ".join(
        message.get("content", "")
        for message in (messages or [])
        if message.get("role") == "user"
    ).lower()
    return _infer_trade(history)


def _extract_basics(text: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    lowered = text.lower()
    if "name is" in lowered:
        data["name"] = text.split("name is", 1)[1].strip().split(".")[0].title()
    trade = _infer_trade(lowered)
    if trade != "other":
        data["trade_category"] = trade
    return data


def _extract_years(text: str) -> int | None:
    match = re.search(r"(\d+)", text)
    return int(match.group(1)) if match else None


def _infer_years_from_session(messages: list[dict[str, Any]] | None) -> int | None:
    for message in reversed(messages or []):
        if message.get("role") != "user":
            continue
        years = _extract_years(message.get("content", ""))
        if years is not None:
            return years
    return None


def _extract_skills(text: str, trade: str) -> list[str]:
    canonical = SKILL_TAGS.get(trade, [])
    lowered = text.lower()
    matched = [skill for skill in canonical if skill.lower() in lowered]
    if matched:
        return matched
    if "," in text:
        return [part.strip() for part in text.split(",") if part.strip()]
    return canonical[:4]


def _extract_business_details(text: str) -> dict[str, Any]:
    lower = text.lower()
    district = next((item for item in DISTRICTS if item.lower() in lower), "Kathmandu")
    savings = next((key for key, tokens in SAVINGS_MAP.items() if any(token in lower for token in tokens)), "under_5L")
    return {
        "district_target": district,
        "savings_range": savings,
        "has_savings": savings != "under_5L",
        "skills": [text.strip()],
    }


def _generic_checklist(trade: str, district: str) -> list[dict[str, Any]]:
    return _validate_checklist_items(
        [
            {"category": "Legal & Registration", "week": 1, "task": f"Confirm ward office registration steps for a {trade} business in {district}.", "done": False},
            {"category": "Legal & Registration", "week": 1, "task": "Check whether PAN registration and local municipality approval are required.", "done": False},
            {"category": "Finance & Loans", "week": 2, "task": "List startup budget, emergency reserve, and first 3 months of operating costs.", "done": False},
            {"category": "Finance & Loans", "week": 2, "task": "Compare your savings with cooperative, bank, or remittance-backed loan options.", "done": False},
            {"category": "Location & Equipment", "week": 3, "task": f"Shortlist two possible operating areas in or near {district}.", "done": False},
            {"category": "Location & Equipment", "week": 4, "task": f"Prepare the basic tools and equipment required for your {trade} service.", "done": False},
            {"category": "Operations", "week": 5, "task": "Create a supplier/contact list and simple daily operations checklist.", "done": False},
            {"category": "Operations", "week": 6, "task": "Set simple pricing, quality standards, and customer follow-up steps.", "done": False},
            {"category": "Marketing", "week": 7, "task": "Prepare a Facebook page, WhatsApp number, and referral message for your first customers.", "done": False},
            {"category": "Marketing", "week": 8, "task": "Launch with a small opening offer and collect first customer feedback.", "done": False},
        ]
    )


def _validate_checklist_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [ChecklistItem.model_validate(item).model_dump() for item in items]


def _respond(language: str, en_text: str, ne_text: str) -> str:
    return ne_text if language == "ne" else en_text


def _enum_value(value: Any) -> str | None:
    return value.value if hasattr(value, "value") else value


def _coerce_years(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    match = re.search(r"(\d+)", str(value))
    return int(match.group(1)) if match else None


def _coerce_skills(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [part.strip() for part in value.split(",") if part.strip()]
    return []


def _coerce_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        if value.lower() in {"true", "yes"}:
            return True
        if value.lower() in {"false", "no"}:
            return False
    return None


def _clean_trade(value: Any) -> str | None:
    if isinstance(value, str) and value in set(SKILL_TAGS) | {"other"}:
        return value
    return None


def _clean_district(value: Any) -> str | None:
    if isinstance(value, str):
        for district in DISTRICTS:
            if district.lower() == value.lower():
                return district
    return None
