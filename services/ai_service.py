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

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None

SKILL_TAGS = {
    "construction": ["formwork", "concrete pouring", "site supervision", "scaffolding", "MEP works", "safety management", "equipment operation", "masonry", "plumbing", "electrical fitting"],
    "hospitality": ["front desk", "housekeeping", "food service", "kitchen prep", "event management", "bartending", "guest relations", "hotel operations", "tour guiding", "cleaning supervision"],
    "manufacturing": ["machine operation", "quality control", "assembly line", "welding", "fabrication", "inventory management", "forklift operation", "production planning", "packaging"],
    "agriculture": ["crop management", "irrigation", "livestock", "greenhouse", "organic farming", "harvesting", "agri-machinery", "soil testing", "pest control", "market selling"],
    "transport": ["heavy vehicle driving", "logistics", "route planning", "vehicle maintenance", "cargo handling", "fleet management", "customer service", "GPS navigation"],
    "tech": ["web development", "data entry", "IT support", "networking", "social media", "graphic design", "video editing", "mobile apps", "customer support", "digital marketing"],
    "domestic": ["childcare", "elder care", "cooking", "cleaning", "home management", "tutoring", "driving", "security", "laundry", "event catering"],
}

TRADE_KEYWORDS = {
    "construction": ["construction", "builder", "mason", "site", "plumbing", "electric", "scaffold"],
    "hospitality": ["hotel", "restaurant", "hospitality", "kitchen", "housekeeping", "guest"],
    "manufacturing": ["factory", "manufacturing", "welding", "assembly", "machine"],
    "agriculture": ["farm", "agriculture", "crop", "livestock", "harvest"],
    "domestic": ["housemaid", "domestic", "caregiver", "childcare", "elder care", "home"],
    "transport": ["driver", "transport", "logistics", "cargo", "vehicle"],
    "tech": ["tech", "it", "developer", "computer", "digital", "support"],
}

DISTRICTS = ["Kathmandu", "Lalitpur", "Bhaktapur", "Pokhara", "Chitwan", "Biratnagar", "Butwal"]
SAVINGS_MAP = {
    "under_5L": ["under 5", "under_5l", "below 5", "less than 5"],
    "5L_to_20L": ["5l_to_20l", "5 to 20", "5-20", "between 5 and 20"],
    "20L_to_50L": ["20l_to_50l", "20 to 50", "20-50", "between 20 and 50"],
    "above_50L": ["above 50", "more than 50", "over 50", "above_50l"],
}

EXTRACT_PATTERN = re.compile(r"<extract>(.*?)</extract>", re.DOTALL)


def get_welcome_message(language: str) -> str:
    if language == "ne":
        return "नमस्ते! म FARKA हुँ। म विदेशमा काम गर्ने नेपालीहरूलाई घर फर्कने बाटो खोज्न मद्दत गर्छु। पहिले भन्नुस् — अहिले तपाईं कहाँ हुनुहुन्छ?"
    return "Namaste! I'm FARKA. I help Nepali workers abroad find their path back home — whether that's a job or starting a business. First, tell me: where are you right now?"


def _stage_goal(stage: str) -> str:
    return {
        "language_set": "Ask where they are now and what work they did abroad. Be warm and curious.",
        "collecting_basics": "Extract current_location and trade_category. Ask about years of experience.",
        "collecting_experience": "Extract years_experience. Ask if they want a job or to start a business.",
        "path_decision": "Determine if they want job_seeker or business_starter path. Set profile.path.",
        "collecting_skills": "Show skill tag suggestions for their trade from the canonical skill tags list. Ask them to confirm which apply to them. Extract confirmed skills as a list.",
        "collecting_business_details": "Ask which district they want to return to, their savings range, and their specific business idea. Be encouraging.",
        "profile_complete": "Tell them their profile is ready. Say you are now searching or generating. Set redirect.",
    }.get(stage, "Keep the conversation moving helpfully.")


def _safe_json_loads(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except Exception:
        return {}


def _parse_extract(response_text: str) -> tuple[str, dict[str, Any]]:
    match = EXTRACT_PATTERN.search(response_text or "")
    if not match:
        return response_text.strip(), {}
    extract_text = match.group(1).strip()
    reply = EXTRACT_PATTERN.sub("", response_text).strip()
    return reply, _safe_json_loads(extract_text)


def _fallback_process(session: ChatSession, user_message: str) -> dict[str, Any]:
    stage = session.workflow_stage.value if hasattr(session.workflow_stage, "value") else str(session.workflow_stage)
    text = user_message.strip()
    lower = text.lower()
    extracted: dict[str, Any] = {}
    reply = "Thanks. Tell me a bit more."
    next_stage = stage
    redirect = None

    if stage == "language_set":
        extracted["current_location"] = text
        extracted["trade_category"] = _infer_trade(lower)
        next_stage = "collecting_basics"
        reply = _respond(
            session.language,
            "Thank you. What kind of work did you do abroad, and what is your name if you want to share it?",
            "धन्यवाद। विदेशमा कस्तो काम गर्नुहुन्थ्यो, र चाहनुहुन्छ भने आफ्नो नाम पनि भन्नुस्।",
        )
    elif stage == "collecting_basics":
        extracted.update(_extract_basics(text))
        if "trade_category" not in extracted:
            extracted["trade_category"] = _infer_trade(lower)
        next_stage = "collecting_experience"
        reply = _respond(
            session.language,
            "How many years of experience do you have in this work?",
            "यो काममा तपाईंको कति वर्षको अनुभव छ?",
        )
    elif stage == "collecting_experience":
        extracted["years_experience"] = _extract_years(lower)
        next_stage = "path_decision"
        reply = _respond(
            session.language,
            "When you return to Nepal, do you want a job or do you want to start your own business?",
            "नेपाल फर्केपछि तपाईं जागिर खोज्न चाहनुहुन्छ कि आफ्नै व्यवसाय सुरु गर्न चाहनुहुन्छ?",
        )
    elif stage == "path_decision":
        extracted["path"] = "business_starter" if any(word in lower for word in ["business", "shop", "start my own", "व्यवसाय"]) else "job_seeker"
        if extracted["path"] == "job_seeker":
            next_stage = "collecting_skills"
            inferred_trade = _infer_trade_from_session(session.messages)
            suggestions = SKILL_TAGS.get(inferred_trade, [])[:6]
            if suggestions:
                skill_text = ", ".join(suggestions)
                reply = _respond(
                    session.language,
                    f"These skills are common for your trade: {skill_text}. Which of these match you? You can add your own too.",
                    f"तपाईंको कामसँग मिल्ने सीपहरू यस्ता छन्: {skill_text}. यीमध्ये कुन-कुन तपाईंलाई मिल्छ? आफ्नै सीप पनि थप्न सक्नुहुन्छ।",
                )
            else:
                reply = _respond(
                    session.language,
                    "Tell me the main skills you use in your work. You can list them one by one.",
                    "तपाईंले आफ्नो काममा प्रयोग गर्ने मुख्य सीपहरू भन्नुस्। एक-एक गरेर सूची दिन सक्नुहुन्छ।",
                )
        else:
            next_stage = "collecting_business_details"
            reply = _respond(
                session.language,
                "Which district do you want to return to, how much savings do you have, and what business do you want to start?",
                "तपाईं कुन जिल्लामा फर्कन चाहनुहुन्छ, कति बचत छ, र कस्तो व्यवसाय सुरु गर्न चाहनुहुन्छ?",
            )
    elif stage == "collecting_skills":
        inferred_trade = _infer_trade_from_session(session.messages)
        extracted["skills"] = _extract_skills(text, inferred_trade)
        next_stage = "job_matching"
        redirect = "jobs"
        reply = _respond(
            session.language,
            "Your profile is ready. I am now searching for jobs that match your skills.",
            "तपाईंको प्रोफाइल तयार भयो। अब तपाईंको सीपसँग मिल्ने जागिर खोज्दैछु।",
        )
    elif stage == "collecting_business_details":
        extracted.update(_extract_business_details(text))
        next_stage = "checklist_generated"
        redirect = "checklist"
        reply = _respond(
            session.language,
            "Your profile is ready. I am now building your business checklist.",
            "तपाईंको प्रोफाइल तयार भयो। अब तपाईंको व्यवसाय चेकलिस्ट बनाउँदैछु।",
        )

    return {"reply": reply, "extracted_data": extracted, "next_stage": next_stage, "redirect": redirect}


def process_message(session: ChatSession, user_message: str) -> dict[str, Any]:
    stage = session.workflow_stage.value if hasattr(session.workflow_stage, "value") else str(session.workflow_stage)
    language = session.language.value if hasattr(session.language, "value") else str(session.language)
    language_instruction = get_language_instruction(language)
    last_messages = json.dumps((session.messages or [])[-3:], ensure_ascii=False)

    if not client:
        return _fallback_process(session, user_message)

    system_prompt = f"""
You are FARKA, a friendly career and business advisor for Nepali migrant workers returning home.
{language_instruction}
Current workflow stage: {stage}
Your goal at this stage: {_stage_goal(stage)}
Conversation so far: {last_messages}

IMPORTANT: At the end of your response, output a JSON block wrapped in <extract></extract> tags.
This JSON must contain any data you extracted from the user's message.
If nothing extracted, output: <extract>{{}}</extract>
Also include "next_stage" and "redirect" (null or "jobs" or "checklist") in the extract block.
""".strip()

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.3,
        )
        content = response.choices[0].message.content or ""
        reply, extracted = _parse_extract(content)
        next_stage = extracted.pop("next_stage", stage)
        redirect = extracted.pop("redirect", None)
        if not reply:
            reply = _fallback_process(session, user_message)["reply"]
        return {"reply": reply, "extracted_data": extracted, "next_stage": next_stage, "redirect": redirect}
    except Exception:
        return _fallback_process(session, user_message)


def generate_checklist(profile: Profile) -> dict[str, Any]:
    language = profile.language_pref.value if hasattr(profile.language_pref, "value") else str(profile.language_pref or "en")
    trade = profile.trade_category.value if hasattr(profile.trade_category, "value") else str(profile.trade_category or "other")
    district = profile.district_target or "Kathmandu"
    savings = profile.savings_range.value if hasattr(profile.savings_range, "value") else str(profile.savings_range or "under_5L")
    business_idea = ", ".join(profile.skills or []) or trade

    if not client:
        items = _generic_checklist(trade)
        return {"checklist_items": items, "raw_ai_output": json.dumps(items, ensure_ascii=False)}

    system_prompt = f"""
You are a business advisor for Nepal. Generate a realistic 8-week business launch checklist for a returning Nepali migrant worker.
Be specific to Nepal. Output ONLY valid JSON.
{get_language_instruction(language)}
""".strip()
    user_prompt = (
        f"Worker profile: Trade={trade}, Target district={district}, Savings={savings}, "
        f"Business idea: {business_idea}. "
        "Generate checklist as JSON array: [{category: str, week: int, task: str, done: false}]. "
        "Include categories: Legal & Registration, Finance & Loans, Location & Equipment, Marketing, Operations."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )
        raw = response.choices[0].message.content or "[]"
        items = _validate_checklist_items(json.loads(raw))
        if not isinstance(items, list) or not items:
            raise ValueError("Invalid checklist output")
        return {"checklist_items": items, "raw_ai_output": raw}
    except Exception:
        items = _generic_checklist(trade)
        return {"checklist_items": items, "raw_ai_output": json.dumps(items, ensure_ascii=False)}


def _respond(language: str, en_text: str, ne_text: str) -> str:
    return ne_text if language == "ne" else en_text


def _infer_trade(text: str) -> str:
    for trade, keywords in TRADE_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return trade
    return "other"


def _extract_basics(text: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    if "name is" in text.lower():
        data["name"] = text.split("name is", 1)[1].strip().split(".")[0].title()
    trade = _infer_trade(text.lower())
    if trade != "other":
        data["trade_category"] = trade
    return data


def _extract_years(text: str) -> int | None:
    match = re.search(r"(\d+)", text)
    return int(match.group(1)) if match else None


def _infer_trade_from_session(messages: list[dict[str, Any]] | None) -> str:
    history = " ".join(
        message.get("content", "")
        for message in (messages or [])
        if message.get("role") == "user"
    ).lower()
    return _infer_trade(history)


def _extract_skills(text: str, trade: str) -> list[str]:
    canonical = SKILL_TAGS.get(trade, [])
    lowered = text.lower()
    matched = [skill for skill in canonical if skill.lower() in lowered]
    if matched:
        return matched
    return canonical[:3]


def _extract_business_details(text: str) -> dict[str, Any]:
    lower = text.lower()
    district = next((item for item in DISTRICTS if item.lower() in lower), None)
    savings = next(
        (key for key, tokens in SAVINGS_MAP.items() if any(token in lower for token in tokens)),
        "under_5L",
    )
    return {
        "district_target": district or "Kathmandu",
        "savings_range": savings,
        "has_savings": savings != "under_5L" or "saving" in lower or "बचत" in lower,
        "skills": [text.strip()],
    }


def _generic_checklist(trade: str) -> list[dict[str, Any]]:
    return _validate_checklist_items([
        {"category": "Legal & Registration", "week": 1, "task": f"Choose a clear {trade} business name and confirm ward-level registration requirements.", "done": False},
        {"category": "Legal & Registration", "week": 1, "task": "Visit the local municipality office to understand registration documents and tax setup.", "done": False},
        {"category": "Finance & Loans", "week": 2, "task": "Estimate startup budget, monthly operating costs, and break-even target.", "done": False},
        {"category": "Finance & Loans", "week": 2, "task": "Compare personal savings with cooperative, bank, or remittance-backed loan options.", "done": False},
        {"category": "Location & Equipment", "week": 3, "task": "Shortlist two operating locations and compare rent, foot traffic, and access.", "done": False},
        {"category": "Location & Equipment", "week": 4, "task": f"Prepare the essential tools and equipment needed for a small {trade} operation.", "done": False},
        {"category": "Operations", "week": 5, "task": "Create a first-month supplier list and simple pricing sheet.", "done": False},
        {"category": "Operations", "week": 6, "task": "Write daily operations steps, quality checks, and customer handling process.", "done": False},
        {"category": "Marketing", "week": 7, "task": "Create a Facebook page, WhatsApp contact card, and local referral message.", "done": False},
        {"category": "Marketing", "week": 8, "task": "Launch with an opening offer and ask first customers for referrals and testimonials.", "done": False},
    ])


def _validate_checklist_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [ChecklistItem.model_validate(item).model_dump() for item in items]
