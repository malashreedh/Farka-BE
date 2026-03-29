from __future__ import annotations

import io
import json
import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI
import requests

from models import ChatSession, Profile
from schemas import BusinessViabilityOption, ChecklistItem
from services.business_viability_service import build_viability_options
from services.language_service import get_language_instruction
from services.workflow_config import DISTRICT_CHOICES, PATH_CHOICES, SAVINGS_CHOICES, SKILL_TAGS

load_dotenv()

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
FALLBACK_MODELS = [OPENAI_MODEL, "gpt-5.4-mini", "gpt-4o-mini"]
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_MODEL_ID = os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
ELEVENLABS_VOICE_ID_EN = os.getenv("ELEVENLABS_VOICE_ID_EN", ELEVENLABS_VOICE_ID)
ELEVENLABS_VOICE_ID_NE = os.getenv("ELEVENLABS_VOICE_ID_NE", ELEVENLABS_VOICE_ID)
OPENAI_TTS_MODEL = os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
OPENAI_TTS_VOICE = os.getenv("OPENAI_TTS_VOICE", "alloy")
OPENAI_TTS_VOICE_EN = os.getenv("OPENAI_TTS_VOICE_EN", OPENAI_TTS_VOICE)
OPENAI_TTS_VOICE_NE = os.getenv("OPENAI_TTS_VOICE_NE", OPENAI_TTS_VOICE)

TRADE_KEYWORDS = {
    "construction": ["construction", "builder", "mason", "site", "plumbing", "electric", "scaffold", "निर्माण", "मिस्त्री"],
    "hospitality": [
        "hotel",
        "restaurant",
        "hospitality",
        "mcdonald",
        "mcdonalds",
        "server",
        "waiter",
        "waitress",
        "food delivery",
        "food counter",
        "fast food",
        "food service",
        "kitchen",
        "housekeeping",
        "guest",
        "hotel operations",
        "retail",
        "shop",
        "store",
        "cashier",
        "sales",
        "customer service",
        "counter",
        "होटल",
        "रेस्टुरेन्ट",
        "पसल",
        "ग्राहक",
        "सामान बेच",
        "बेच",
        "कस्टमर",
    ],
    "manufacturing": ["factory", "manufacturing", "welding", "assembly", "machine", "फ्याक्ट्री", "मेसिन"],
    "agriculture": ["farm", "agriculture", "crop", "livestock", "harvest", "कृषि", "खेती", "पशुपालन"],
    "domestic": ["housemaid", "domestic", "caregiver", "childcare", "elder care", "home", "घरेलु", "हेरचाह"],
    "transport": ["driver", "transport", "logistics", "cargo", "vehicle", "ड्राइभर", "यातायात"],
    "tech": ["tech", "it", "developer", "computer", "digital", "support", "प्रविधि", "कम्प्युटर"],
}

STAGE_GOALS = {
    "initial": "Greet warmly and ask where the user is currently working or living.",
    "language_set": "Get the user's current location clearly before moving on.",
    "collecting_basics": "Understand what type of work they did abroad and capture trade_category.",
    "collecting_experience": "Find out their years of experience in that work.",
    "path_decision": "Find out whether they want a job in Nepal or want to start a business.",
    "collecting_skills": "Help the user confirm the skills they actually used most in their work.",
    "collecting_business_details": "Collect district, savings range, and a concrete business idea needed for the checklist. Keep asking until all three are known.",
    "job_matching": "Confirm that job matching is underway.",
    "checklist_generated": "Confirm that the business checklist is being prepared or is ready.",
}

DISTRICTS = [
    "Kathmandu",
    "Lalitpur",
    "Bhaktapur",
    "Pokhara",
    "Chitwan",
    "Biratnagar",
    "Butwal",
    "Rupandehi",
    "Dharan",
    "Janakpur",
    "Hetauda",
    "Nepalgunj",
    "Dhangadhi",
]
SMALL_TALK_PATTERNS = {
    "en": {"hi", "hello", "hey", "good morning", "good evening", "namaste", "yo", "start"},
    "ne": {"नमस्ते", "हेलो", "हाई", "हे", "सन्चै", "शुरु"},
}
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

    prompt = _build_system_prompt(stage, language, session)

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
            reply = _compose_guided_reply(
                language=language,
                stage=stage,
                next_stage=clean["next_stage"],
                fields=clean["fields"],
                session=session,
                llm_reply=reply,
            )
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
    business_idea = getattr(profile, "business_idea", None) or _derive_business_idea(profile, trade)

    if not client:
        items = _generic_checklist(business_idea, district)
        return {"checklist_items": items, "raw_ai_output": json.dumps(items, ensure_ascii=False)}

    system_prompt = f"""
You are a Nepal-focused small business advisor.
{get_language_instruction(language)}
Generate a grounded 8-week launch checklist for a returning Nepali migrant worker.
Be realistic, district-aware, specific, and action-oriented.
Assume this is a first-time founder who needs a practical, week-by-week roadmap.
Output ONLY valid JSON.
""".strip()

    user_prompt = (
        f"Profile: trade={trade}, district={district}, savings={savings}, business idea={business_idea}. "
        "Return a JSON array only. Each item must be {category: str, week: int, task: str, done: false}. "
        "Use categories from Legal & Registration, Finance & Loans, Location & Equipment, Marketing, Operations. "
        "Generate 12 to 15 items spread across 8 weeks. Include practical Nepal-specific actions like registration, supplier scouting, "
        "location validation, pilot selling, pricing, and first-customer outreach. Mention the district or local context where useful."
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
            cleaned = _strip_markdown_fences(raw)
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                parsed = parsed.get("checklist_items") or parsed.get("items") or parsed.get("checklist") or []
            items = _validate_checklist_items(parsed)
            if not items:
                raise ValueError("Empty checklist")
            return {"checklist_items": items, "raw_ai_output": cleaned}
        except Exception:
            continue

    items = _generic_checklist(business_idea, district)
    return {"checklist_items": items, "raw_ai_output": json.dumps(items, ensure_ascii=False)}


def transcribe_audio(audio_file: Any, language: str | None = None) -> str:
    if not client:
        return ""

    try:
        prepared_file = _prepare_audio_file(audio_file)
        kwargs: dict[str, Any] = {"model": "whisper-1", "file": prepared_file}
        if language == "ne":
            kwargs["language"] = "ne"
        transcript = client.audio.transcriptions.create(**kwargs)
        return (getattr(transcript, "text", "") or "").strip()
    except Exception:
        return ""


def synthesize_speech(text: str, language: str) -> bytes:
    if not text.strip():
        return b""

    if ELEVENLABS_API_KEY:
        audio_bytes = _synthesize_with_elevenlabs(text, language)
        if audio_bytes:
            return audio_bytes

    if client:
        audio_bytes = _synthesize_with_openai(text, language)
        if audio_bytes:
            return audio_bytes

    try:
        from gtts import gTTS

        tts = gTTS(text=text, lang="ne" if language == "ne" else "en", slow=False)
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        return audio_buffer.read()
    except Exception:
        return b""


def generate_viability_notes(
    trade_category: str,
    district: str,
    savings_amount_npr: int,
    options: list[dict[str, Any]],
) -> list[str | None]:
    if not client or not options:
        return [None] * len(options)

    prompt = (
        "You are helping Nepali returnees evaluate small business options. "
        "Given the computed business options, write one concise note per option. "
        "Each note should mention practical fit, one caution, and why the break-even timeline is believable. "
        "Return ONLY valid JSON in the format {\"notes\": [\"...\", \"...\", \"...\"]}."
    )
    user_payload = {
        "trade_category": trade_category,
        "district": district,
        "savings_amount_npr": savings_amount_npr,
        "options": options,
    }

    for model in FALLBACK_MODELS:
        try:
            response = client.chat.completions.create(
                model=model,
                temperature=0.2,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
                ],
            )
            content = response.choices[0].message.content or "{}"
            parsed = json.loads(content)
            notes = parsed.get("notes", [])
            if isinstance(notes, list):
                return [str(item) if item is not None else None for item in notes[: len(options)]]
        except Exception:
            continue

    return [None] * len(options)


def generate_viability_options(
    trade_category: str,
    district: str,
    savings_amount_npr: int,
    profile: Profile | None = None,
) -> list[dict[str, Any]]:
    language = _enum_value(getattr(profile, "language_pref", None)) or "en"
    business_idea = getattr(profile, "business_idea", None) or _derive_business_idea(profile, trade_category)

    if not client:
        fallback_options = build_viability_options(trade_category, district, savings_amount_npr)
        notes = generate_viability_notes(trade_category, district, savings_amount_npr, fallback_options)
        for option, note in zip(fallback_options, notes, strict=False):
            option["ai_note"] = note
        return fallback_options

    system_prompt = f"""
You are a Nepal-focused business advisor helping a returning migrant worker evaluate realistic small business options.
{get_language_instruction(language)}
Return ONLY valid JSON in this exact shape:
{{
  "options": [
    {{
      "title": "string",
      "fit_reason": "string",
      "startup_cost_npr": 0,
      "working_capital_npr": 0,
      "total_estimated_cost_npr": 0,
      "savings_gap_npr": 0,
      "break_even_months": 0,
      "risk_level": "low",
      "monthly_revenue_range_npr": "string",
      "monthly_cost_range_npr": "string",
      "suggested_first_steps": ["string"],
      "ai_note": "string"
    }}
  ]
}}

Rules:
- Generate exactly 3 options.
- Keep all descriptive text in the user's language.
- risk_level must be one of: low, moderate, high.
- Use realistic Nepal context for the given district.
- One option should be close to the user's stated business idea if one exists.
- The other options should be adjacent, realistic alternatives, not the same repeated categories every time.
- Numbers must be integers in NPR.
- total_estimated_cost_npr must equal startup_cost_npr + working_capital_npr.
- savings_gap_npr must be max(total_estimated_cost_npr - savings_amount_npr, 0).
- break_even_months should be realistic, usually between 4 and 30.
- monthly revenue and cost ranges should be plausible formatted strings like "NPR 120,000 - 165,000".
- suggested_first_steps should contain 3 short, practical steps.
- ai_note should be a concise 1-2 sentence practical assessment.
""".strip()

    user_payload = {
        "trade_category": trade_category,
        "district": district,
        "savings_amount_npr": savings_amount_npr,
        "business_idea": business_idea,
        "language": language,
    }

    for model in FALLBACK_MODELS:
        try:
            response = client.chat.completions.create(
                model=model,
                temperature=0.35,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
                ],
            )
            raw = response.choices[0].message.content or "{}"
            cleaned = _strip_markdown_fences(raw)
            parsed = json.loads(cleaned)
            options = parsed.get("options", [])
            validated = [BusinessViabilityOption.model_validate(item).model_dump() for item in options[:3]]
            if len(validated) == 3:
                return validated
        except Exception:
            continue

    fallback_options = build_viability_options(trade_category, district, savings_amount_npr)
    notes = generate_viability_notes(trade_category, district, savings_amount_npr, fallback_options)
    for option, note in zip(fallback_options, notes, strict=False):
        option["ai_note"] = note
    return fallback_options


def _fallback_process(session: ChatSession, user_message: str) -> dict[str, Any]:
    extracted = _normalize_extracted_data(_heuristic_extract(session, user_message), session)
    language = _enum_value(session.language) or "en"
    stage = _enum_value(session.workflow_stage)
    reply = _compose_guided_reply(
        language=language,
        stage=stage,
        next_stage=extracted["next_stage"],
        fields=extracted["fields"],
        session=session,
        llm_reply=None,
    )
    return {
        "reply": reply,
        "extracted_data": extracted["fields"],
        "next_stage": extracted["next_stage"],
        "redirect": extracted["redirect"],
    }


def _synthesize_with_elevenlabs(text: str, language: str) -> bytes:
    voice_id = ELEVENLABS_VOICE_ID_NE if language == "ne" else ELEVENLABS_VOICE_ID_EN
    try:
        response = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            headers={
                "xi-api-key": ELEVENLABS_API_KEY or "",
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            },
            json={
                "text": text,
                "model_id": ELEVENLABS_MODEL_ID,
                "voice_settings": {"stability": 0.45, "similarity_boost": 0.78},
            },
            timeout=30,
        )
        if response.ok and response.content:
            return response.content
    except Exception:
        return b""
    return b""


def _synthesize_with_openai(text: str, language: str) -> bytes:
    voice = OPENAI_TTS_VOICE_NE if language == "ne" else OPENAI_TTS_VOICE_EN
    try:
        response = client.audio.speech.create(
            model=OPENAI_TTS_MODEL,
            voice=voice,
            input=text,
        )
        content = getattr(response, "content", None)
        if content:
            return content
        if hasattr(response, "read"):
            return response.read()
    except Exception:
        return b""
    return b""


def _strip_markdown_fences(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def _derive_business_idea(profile: Profile | None, trade_category: str) -> str:
    if not profile:
        return trade_category

    # First: check the dedicated business_idea field
    biz = getattr(profile, "business_idea", None)
    if biz and str(biz).strip():
        return str(biz).strip()

    # Fallback: scan skills for non-trade-skill items (legacy behavior)
    skills = [str(item).strip() for item in (getattr(profile, "skills", None) or []) if str(item).strip()]
    filtered = []
    for item in skills:
        lowered = item.lower()
        if lowered in SAVINGS_MAP or item in DISTRICTS:
            continue
        if item in SKILL_TAGS.get(trade_category, []):
            continue
        filtered.append(item)

    if filtered:
        return filtered[-1]
    return trade_category


def _prepare_audio_file(audio_file: Any) -> Any:
    filename = getattr(audio_file, "filename", None) or getattr(audio_file, "name", None) or "voice-message.webm"
    content_type = getattr(audio_file, "content_type", None) or _guess_audio_content_type(filename)

    if hasattr(audio_file, "file"):
        file_obj = audio_file.file
    else:
        file_obj = audio_file

    if hasattr(file_obj, "seek"):
        file_obj.seek(0)
    raw_bytes = file_obj.read() if hasattr(file_obj, "read") else None
    if not raw_bytes:
        raise ValueError("Empty audio payload")

    return (filename, raw_bytes, content_type)


def _guess_audio_content_type(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    return {
        ".webm": "audio/webm",
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".m4a": "audio/mp4",
        ".mp4": "audio/mp4",
        ".ogg": "audio/ogg",
    }.get(suffix, "application/octet-stream")


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


def _build_system_prompt(stage: str, language: str, session: ChatSession) -> str:
    last_messages = json.dumps((session.messages or [])[-6:], ensure_ascii=False)
    trade_category = _enum_value(getattr(getattr(session, "profile", None), "trade_category", None))
    skill_hint = ""
    if stage == "collecting_skills" and trade_category in SKILL_TAGS:
        skill_hint = (
            f"\nSuggested canonical skill tags for {trade_category}: "
            f"{json.dumps(SKILL_TAGS[trade_category], ensure_ascii=False)}"
        )

    return f"""
You are FARKA, a friendly and practical return-migration advisor for Nepali workers abroad.
{get_language_instruction(language)}
Current workflow stage: {stage}
Your goal at this stage: {STAGE_GOALS.get(stage, "Continue the conversation helpfully and extract only what is actually known.")}.
Conversation so far: {last_messages}
{skill_hint}

Behavior rules:
- Sound warm, practical, and trustworthy.
- Be conversational, respectful, and calm.
- Respond like a thoughtful human guide, not a questionnaire or dropdown menu.
- Ask only the next most useful question.
- Keep replies concise and natural, like a real product assistant.
- Use Nepal-specific context when helpful.
- Only advance the stage when the required information has actually been collected.
- If the user gives multiple useful facts in one message, use all of them.
- Always use the existing conversation context before asking for something again.
- Do not list canned work categories unless the user explicitly asks for examples.
- If the user says something broad like "I worked in hotels" or "I was in construction", acknowledge it and ask one natural follow-up.
- For job seekers, keep skill tags in English internally.
- business_idea is the specific business the user wants to START in Nepal (e.g. "restaurant", "tailoring shop", "grocery store"). This is DIFFERENT from trade_category which is their past work abroad. A construction worker can want to open a restaurant.
- Do not move to checklist generation unless district_target, savings_range, and business_idea are all known.

At the very end, output one JSON block inside <extract></extract>.
Use this exact shape:
<extract>{{
  "name": null,
  "current_location": null,
  "trade_category": null,
  "years_experience": null,
  "path": null,
  "skills": [],
  "business_idea": null,
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


def _normalize_extracted_data(extracted: dict[str, Any], session: ChatSession) -> dict[str, Any]:
    stage = _enum_value(session.workflow_stage)
    profile = getattr(session, "profile", None)
    inferred_years = _infer_years_from_session(session.messages)
    inferred_path = _infer_path_from_messages(session.messages)
    inferred_trade = _infer_trade_from_session(session.messages)
    extracted_trade = _meaningful_trade(_clean_trade(extracted.get("trade_category")))
    profile_trade = _meaningful_trade(_enum_value(getattr(profile, "trade_category", None)))
    resolved_trade = _resolve_trade_category(session.messages, extracted_trade, profile_trade, inferred_trade)
    inferred_district = _infer_district_from_messages(session.messages)
    inferred_savings = _infer_savings_from_messages(session.messages)
    inferred_location = _infer_current_location_from_messages(session.messages)
    inferred_skills = _infer_skills_from_messages(
        session.messages,
        resolved_trade,
    )
    draft_skills = _coerce_skills(extracted.get("skills")) or getattr(profile, "skills", None) or inferred_skills
    inferred_biz = _infer_business_idea_from_messages(session.messages)
    raw_biz = extracted.get("business_idea")
    business_idea = (
        raw_biz.strip() if isinstance(raw_biz, str) and raw_biz.strip() else None
    ) or getattr(profile, "business_idea", None) or inferred_biz

    fields = {
        "name": extracted.get("name") or getattr(profile, "name", None),
        "current_location": extracted.get("current_location") or getattr(profile, "current_location", None) or inferred_location,
        "trade_category": resolved_trade,
        "years_experience": _coerce_years(extracted.get("years_experience")) or getattr(profile, "years_experience", None) or inferred_years,
        "path": (
            extracted.get("path")
            if extracted.get("path") in PATH_CHOICES or extracted.get("path") == "undecided"
            else _meaningful_path(_enum_value(getattr(profile, "path", None))) or inferred_path
        ),
        "skills": _clean_business_context_values(
            draft_skills,
            _clean_district(extracted.get("district_target")) or getattr(profile, "district_target", None) or inferred_district,
            extracted.get("savings_range")
            if extracted.get("savings_range") in SAVINGS_CHOICES
            else _enum_value(getattr(profile, "savings_range", None)) or inferred_savings,
        ),
        "business_idea": business_idea,
        "district_target": _clean_district(extracted.get("district_target")) or getattr(profile, "district_target", None) or inferred_district,
        "savings_range": (
            extracted.get("savings_range")
            if extracted.get("savings_range") in SAVINGS_CHOICES
            else _enum_value(getattr(profile, "savings_range", None)) or inferred_savings
        ),
        "has_savings": _coerce_bool(extracted.get("has_savings")),
    }
    if fields["has_savings"] is None and fields["savings_range"] is not None:
        fields["has_savings"] = fields["savings_range"] != "under_5L"

    next_stage, redirect = _resolve_progress(stage, fields, extracted.get("redirect"))

    return {"fields": {k: v for k, v in fields.items() if v not in (None, [], "")}, "next_stage": next_stage, "redirect": redirect}


def _infer_trade(text: str) -> str:
    scores: dict[str, int] = {}
    for trade, keywords in TRADE_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in text)
        if score:
            scores[trade] = score
    if scores:
        priority = {
            "hospitality": 7,
            "manufacturing": 6,
            "construction": 5,
            "transport": 4,
            "agriculture": 3,
            "domestic": 2,
            "tech": 1,
        }
        return max(scores.items(), key=lambda item: (item[1], priority.get(item[0], 0)))[0]
    return "other"


def _trade_keyword_score(text: str, trade: str | None) -> int:
    if not trade or trade not in TRADE_KEYWORDS:
        return 0
    lowered = text.lower()
    return sum(1 for keyword in TRADE_KEYWORDS[trade] if keyword in lowered)


def _resolve_trade_category(
    messages: list[dict[str, Any]] | None,
    extracted_trade: str | None,
    profile_trade: str | None,
    inferred_trade: str | None,
) -> str | None:
    history = " ".join(
        message.get("content", "")
        for message in (messages or [])
        if message.get("role") == "user"
    )
    candidates = [candidate for candidate in [extracted_trade, profile_trade, _meaningful_trade(inferred_trade)] if candidate]
    if not candidates:
        return None
    best = candidates[0]
    best_score = _trade_keyword_score(history, best)
    for candidate in candidates[1:]:
        score = _trade_keyword_score(history, candidate)
        if score > best_score:
            best = candidate
            best_score = score
    return best


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


def _infer_business_idea_from_messages(messages: list[dict[str, Any]] | None) -> str | None:
    """Scan conversation for explicit business idea mentions."""
    patterns = [
        r"(?:want to|going to|plan to|like to)\s+(?:start|open|run|build)\s+(?:a\s+)?(.+?)(?:\s+in\s+|\s+at\s+|[,.]|$)",
        r"(?:start|open|run)\s+(?:a\s+)?(.+?)(?:\s+business|\s+shop|\s+in\s+|[,.]|$)",
        r"(?:business idea is|my idea is|thinking of)\s+(?:a\s+)?(.+?)(?:[,.]|$)",
        r"(?:सुरु गर्न|खोल्न)\s+चाहन्छु\s*[:.]?\s*(.+?)(?:[,।.]|$)",
    ]
    for message in reversed(messages or []):
        if message.get("role") != "user":
            continue
        content = message.get("content", "").strip()
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                idea = match.group(1).strip(" .,")
                if idea and len(idea) >= 3 and idea.lower() not in {"a", "my", "the", "some", "business"}:
                    return idea
    return None


def _infer_path_from_messages(messages: list[dict[str, Any]] | None) -> str | None:
    history = " ".join(
        message.get("content", "")
        for message in (messages or [])
        if message.get("role") == "user"
    ).lower()
    if any(token in history for token in ["business", "own business", "shop", "startup", "व्यवसाय", "पसल"]):
        return "business_starter"
    if any(token in history for token in ["job", "employment", "find work", "jagir", "जागिर"]):
        return "job_seeker"
    return None


def _infer_district_from_messages(messages: list[dict[str, Any]] | None) -> str | None:
    history = " ".join(
        message.get("content", "")
        for message in (messages or [])
        if message.get("role") == "user"
    )
    return _clean_district(history)


def _infer_current_location_from_messages(messages: list[dict[str, Any]] | None) -> str | None:
    for message in reversed(messages or []):
        if message.get("role") != "user":
            continue
        content = message.get("content", "")
        location = _extract_current_location(content) or _normalize_freeform_location(content)
        if location:
            return location
    return None


def _infer_savings_from_messages(messages: list[dict[str, Any]] | None) -> str | None:
    history = " ".join(
        message.get("content", "")
        for message in (messages or [])
        if message.get("role") == "user"
    ).lower()
    for key, tokens in SAVINGS_MAP.items():
        if any(token in history for token in tokens):
            return key
    return _extract_savings_range_from_amount(history)


def _extract_savings_range_from_amount(text: str) -> str | None:
    lowered = text.lower()
    lakh_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:lakh|lakhs|लाख|लाखs)", lowered)
    if lakh_match:
        amount_lakh = float(lakh_match.group(1))
        if amount_lakh < 5:
            return "under_5L"
        if amount_lakh <= 20:
            return "5L_to_20L"
        if amount_lakh <= 50:
            return "20L_to_50L"
        return "above_50L"

    npr_match = re.search(r"npr\s*([\d,]+)", lowered)
    if npr_match:
        amount_npr = int(npr_match.group(1).replace(",", ""))
        if amount_npr < 500000:
            return "under_5L"
        if amount_npr <= 2000000:
            return "5L_to_20L"
        if amount_npr <= 5000000:
            return "20L_to_50L"
        return "above_50L"
    return None


def _infer_skills_from_messages(messages: list[dict[str, Any]] | None, trade: str | None) -> list[str]:
    history = " ".join(
        message.get("content", "")
        for message in (messages or [])
        if message.get("role") == "user"
    )
    return _extract_skills(history, trade or "other")


def _extract_skills(text: str, trade: str) -> list[str]:
    canonical = SKILL_TAGS.get(trade, [])
    lowered = text.lower()
    matched = [skill for skill in canonical if skill.lower() in lowered]
    if matched:
        return matched
    inferred: list[str] = []
    if trade == "hospitality":
        if any(token in lowered for token in ["customer", "customer service", "guest", "ग्राहक", "कस्टमर"]):
            inferred.append("guest relations")
        if any(token in lowered for token in ["cashier", "billing", "counter", "cash", "bill", "बेच", "पसल"]):
            inferred.append("front desk")
        if any(token in lowered for token in ["store", "shop", "retail", "inventory", "stock", "सामान"]):
            inferred.append("hotel operations")
    if inferred:
        return list(dict.fromkeys(inferred))
    if "," in text:
        return [part.strip() for part in text.split(",") if part.strip()]
    return []


def _extract_business_details(text: str) -> dict[str, Any]:
    lower = text.lower()
    district = _extract_district_from_text(text)
    savings = next((key for key, tokens in SAVINGS_MAP.items() if any(token in lower for token in tokens)), None) or _extract_savings_range_from_amount(text)
    business_idea = _extract_business_idea(text, district, savings)
    data: dict[str, Any] = {}
    if district:
        data["district_target"] = district
    if savings:
        data["savings_range"] = savings
        data["has_savings"] = savings != "under_5L"
    if business_idea:
        data["skills"] = [business_idea]
    return data


def _heuristic_extract(session: ChatSession, user_message: str) -> dict[str, Any]:
    trade = _infer_trade(user_message.lower())
    path = _infer_path_from_messages([{"role": "user", "content": user_message}])
    stage = _enum_value(session.workflow_stage)
    direct_location = _extract_current_location(user_message)
    if not direct_location and stage in {"initial", "language_set"} and not _is_small_talk_text(user_message):
        direct_location = _normalize_freeform_location(user_message)
    extracted: dict[str, Any] = {
        "current_location": direct_location,
        "trade_category": None if trade == "other" else trade,
        "years_experience": _extract_years(user_message),
        "path": path,
        "skills": _extract_skills(user_message, trade if trade != "other" else _infer_trade_from_session(session.messages)),
    }
    active_path = path or _meaningful_path(_enum_value(getattr(getattr(session, "profile", None), "path", None)))
    if active_path == "business_starter":
        extracted.update(_extract_business_details(user_message))
        biz_idea = _infer_business_idea_from_messages([{"role": "user", "content": user_message}])
        if biz_idea:
            extracted["business_idea"] = biz_idea
    return extracted


def _resolve_progress(stage: str, fields: dict[str, Any], redirect_hint: str | None) -> tuple[str, str | None]:
    redirect = redirect_hint
    has_path = fields["path"] in {"job_seeker", "business_starter"}
    has_experience = fields["years_experience"] is not None
    has_skills = bool(fields["skills"])
    has_business_idea = bool(fields.get("business_idea"))
    has_business_details = bool(fields["district_target"] and fields["savings_range"] and has_business_idea)

    # Terminal states — profile complete, redirect to results
    if has_path and fields["path"] == "job_seeker" and has_experience and has_skills:
        return "job_matching", "jobs"
    if has_path and fields["path"] == "business_starter" and has_business_details:
        return "checklist_generated", "checklist"

    # Gathering phase — ask location, then trade, then job/business decision early
    if not fields["current_location"]:
        return "language_set", redirect
    if not fields["trade_category"]:
        return "collecting_basics", redirect
    if not has_path:
        return "path_decision", redirect

    # Branch: job seeker needs experience + skills
    if fields["path"] == "job_seeker":
        if not has_experience:
            return "collecting_experience", redirect
        return "collecting_skills", redirect

    # Branch: business starter needs details (experience is optional)
    return "collecting_business_details", redirect


def _compose_guided_reply(
    language: str,
    stage: str,
    next_stage: str,
    fields: dict[str, Any],
    session: ChatSession,
    llm_reply: str | None,
) -> str:
    llm_reply = (llm_reply or "").strip()
    if _use_llm_reply(llm_reply, next_stage):
        return llm_reply

    if stage in {"initial", "language_set"} and _is_small_talk_message(session.messages):
        return _respond(
            language,
            "Namaste. I can help with jobs or business options back in Nepal. To begin, which country or city are you working in right now?",
            "नमस्ते। म तपाईंलाई नेपालमा जागिर वा व्यवसायको विकल्पबारे सहयोग गर्न सक्छु। सुरु गर्न, तपाईं अहिले कुन देश वा सहरमा काम गर्दै हुनुहुन्छ?",
        )
    if next_stage == "language_set":
        return _respond(
            language,
            "Which country or city are you working in right now?",
            "तपाईं अहिले कुन देश वा सहरमा काम गर्दै हुनुहुन्छ?",
        )
    if next_stage == "collecting_basics":
        return _respond(
            language,
            "Thank you. What kind of work were you doing abroad, and what was your role like day to day?",
            "धन्यवाद। विदेशमा तपाईंले कस्तो काम गर्नुहुन्थ्यो, र दिनहुँको भूमिका कस्तो थियो?",
        )
    if next_stage == "collecting_experience":
        role_summary = _recent_work_summary(session.messages, fields)
        return _respond(
            language,
            f"That helps. About how many years of experience do you have in {role_summary}?",
            f"बुझें। {role_summary} जस्तो काममा तपाईंको करिब कति वर्षको अनुभव छ?",
        )
    if next_stage == "path_decision":
        trade_label = fields.get("trade_category")
        return _respond(
            language,
            (
                f"You already have useful experience{f' in {trade_label}' if trade_label else ''}. "
                "When you return to Nepal, would it help more if I focused on finding you a job or shaping a small business plan?"
            ),
            "तपाईंको अनुभव उपयोगी देखिन्छ। नेपाल फर्केपछि म जागिरतर्फ बढी सहयोग गरूँ कि सानो व्यवसायको योजना बनाउनतर्फ?",
        )
    if next_stage == "collecting_skills":
        return _respond(
            language,
            "Great. To match the right jobs, tell me the skills, tools, or day-to-day responsibilities you used most often in that work.",
            "राम्रो। मिल्दो जागिर छान्न, त्यो काममा तपाईंले सबैभन्दा धेरै प्रयोग गरेका सीप, औजार, वा जिम्मेवारीहरू भन्नुस्।",
        )
    if next_stage == "collecting_business_details":
        missing_district = not fields.get("district_target")
        missing_savings = not fields.get("savings_range")
        missing_idea = not fields.get("business_idea")
        savings = ", ".join(SAVINGS_CHOICES)

        if missing_district and missing_savings and missing_idea:
            return _respond(
                language,
                f"Good choice. So I can make the plan realistic, tell me three things: what business do you want to start, which district in Nepal, and your rough savings range ({savings}).",
                f"राम्रो छनोट। योजना व्यवहारिक बनाउन तीन कुरा भन्नुस्: कस्तो व्यवसाय सुरु गर्न चाहनुहुन्छ, नेपालको कुन जिल्लामा, र बचतको दायरा ({savings})।",
            )
        if missing_idea:
            return _respond(
                language,
                "What kind of business do you want to start in Nepal? For example: restaurant, grocery shop, tailoring, farming, etc.",
                "तपाईं नेपालमा कस्तो व्यवसाय सुरु गर्न चाहनुहुन्छ? उदाहरण: रेस्टुरेन्ट, किराना पसल, सिलाइ, कृषि, आदि।",
            )
        if missing_district:
            return _respond(
                language,
                "Which district in Nepal do you want to start your business in?",
                "तपाईं नेपालको कुन जिल्लामा व्यवसाय सुरु गर्न चाहनुहुन्छ?",
            )
        if missing_savings:
            return _respond(
                language,
                f"What is your current savings range: {savings}?",
                f"तपाईंको बचतको दायरा कुन हो: {savings}?",
            )
        return _respond(
            language,
            "Thanks. I have enough to build a realistic business roadmap now.",
            "धन्यवाद। अब व्यवहारिक व्यवसाय योजना बनाउन पुग्ने जानकारी मसँग छ।",
        )
    if next_stage == "job_matching":
        return _respond(
            language,
            "Your profile looks complete. I’m matching you with Nepal-based roles now.",
            "तपाईंको प्रोफाइल पूरा भयो। अब नेपालका मिल्दो भूमिकासँग म्याच गर्दैछु।",
        )
    if next_stage == "checklist_generated":
        return _respond(
            language,
            "Your profile is ready. I’m preparing a practical Nepal business checklist now.",
            "तपाईंको प्रोफाइल तयार भयो। अब नेपालका लागि व्यवहारिक व्यवसाय चेकलिस्ट तयार गर्दैछु।",
        )
    return llm_reply or _respond(language, "Thanks. Tell me a bit more so I can guide you properly.", "धन्यवाद। म तपाईंलाई राम्रोसँग मार्गदर्शन गर्न अझै अलि जानकारी दिनुस्।")


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


def _use_llm_reply(reply: str | None, next_stage: str) -> bool:
    cleaned = (reply or "").strip()
    if not cleaned:
        return False
    if len(cleaned) < 18:
        return False
    checks = {
        "language_set": ["where", "country", "city", "कहाँ", "देश", "सहर"],
        "collecting_basics": ["work", "role", "day", "काम", "भूमिका", "जिम्मेवारी"],
        "collecting_experience": ["year", "years", "वर्ष"],
        "path_decision": ["job", "business", "जागिर", "व्यवसाय"],
        "collecting_skills": ["skill", "tasks", "tools", "सीप", "जिम्मेवारी", "कामहरू"],
        "collecting_business_details": ["district", "savings", "business", "जिल्ला", "बचत", "व्यवसाय"],
    }
    tokens = checks.get(next_stage)
    if not tokens:
        return True
    lowered = cleaned.lower()
    return any(token in lowered for token in tokens)


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


def _recent_work_summary(messages: list[dict[str, Any]] | None, fields: dict[str, Any]) -> str:
    history = " ".join(
        str(message.get("content", ""))
        for message in (messages or [])
        if message.get("role") == "user"
    ).lower()

    if any(token in history for token in ["mcdonald", "mcdonalds", "server", "restaurant", "food service", "waiter", "waitress"]):
        if any(token in history for token in ["driver", "delivery", "ride", "gाडी", "चलाओ", "चगाओ"]):
            return "restaurant and delivery work"
        return "restaurant or customer service work"
    if any(token in history for token in ["shop", "store", "retail", "cashier", "counter", "पसल", "सामान बेच", "कस्टमर", "ग्राहक"]):
        if any(token in history for token in ["driver", "delivery", "gाडी", "चलाओ", "चगाओ"]):
            return "shop and delivery work"
        return "shop or customer-facing work"

    skills = _coerce_skills(fields.get("skills"))
    if skills:
        if len(skills) == 1:
            return skills[0]
        return ", ".join(skills[:2])

    for message in reversed(messages or []):
        if message.get("role") != "user":
            continue
        content = str(message.get("content", "")).strip()
        lowered = content.lower()
        if any(token in lowered for token in ["worked", "work", "job", "role", "काम", "गर", "थे"]):
            shortened = re.sub(r"^\s*(i worked in|i worked as|i was working in|मैले|म)\s*", "", content, flags=re.IGNORECASE).strip(" .")
            if shortened:
                return shortened[:80]

    trade_category = fields.get("trade_category")
    readable = {
        "construction": "construction or site work",
        "hospitality": "customer-facing service work",
        "manufacturing": "factory or production work",
        "agriculture": "agriculture or farm work",
        "domestic": "domestic or care work",
        "transport": "driving or transport work",
        "tech": "technical or digital work",
    }
    return readable.get(str(trade_category), "that kind of work")


def _clean_business_context_values(values: list[str], district: str | None, savings_range: str | None) -> list[str]:
    cleaned: list[str] = []
    savings_tokens = set()
    if savings_range and savings_range in SAVINGS_MAP:
        savings_tokens.update(token.lower() for token in SAVINGS_MAP[savings_range])

    for raw in values:
        item = str(raw).strip()
        if not item:
            continue
        lowered = item.lower()
        if district and lowered == district.lower():
            continue
        if lowered in SAVINGS_CHOICES or lowered in savings_tokens:
            continue
        if lowered in {"business", "small business", "own business", "व्यवसाय", "start business"}:
            continue
        if len(item) < 4:
            continue
        cleaned.append(item)
    return cleaned


def _extract_business_idea(text: str, district: str | None, savings: str | None) -> str | None:
    cleaned = text.strip()
    if not cleaned:
        return None

    candidate = cleaned
    if district:
        candidate = re.sub(re.escape(district), "", candidate, flags=re.IGNORECASE)
    for key, tokens in SAVINGS_MAP.items():
        for token in tokens:
            candidate = re.sub(re.escape(token), "", candidate, flags=re.IGNORECASE)
    candidate = re.sub(r"\b\d+(?:\.\d+)?\s*(?:lakh|lakhs|लाख|lakhs?)\b", " ", candidate, flags=re.IGNORECASE)
    candidate = re.sub(r"\bnpr\s*[\d,]+\b", " ", candidate, flags=re.IGNORECASE)
    candidate = re.sub(r"\b(district|savings|range|target|my|is|in|at|want|to|start|business|idea)\b", " ", candidate, flags=re.IGNORECASE)
    candidate = re.sub(r"\b(i have|i need|from somewhere|already have|have)\b", " ", candidate, flags=re.IGNORECASE)
    candidate = re.sub(r"[,:;.\-_/]+", " ", candidate)
    candidate = re.sub(r"\s+", " ", candidate).strip()

    if not candidate or len(candidate) < 4:
        return None
    if candidate.lower() in {district.lower() for district in DISTRICTS}:
        return None
    return candidate


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


def _meaningful_trade(value: str | None) -> str | None:
    if value in {None, "", "other"}:
        return None
    return value


def _meaningful_path(value: str | None) -> str | None:
    if value in {None, "", "undecided"}:
        return None
    return value


def _clean_district(value: Any) -> str | None:
    if isinstance(value, str):
        for district in DISTRICTS:
            if district.lower() in value.lower():
                return district
        fallback = _normalize_district_text(value)
        if fallback:
            return fallback
    return None


def _extract_district_from_text(text: str) -> str | None:
    for district in DISTRICTS:
        if district.lower() in text.lower():
            return district

    patterns = [
        r"(?:target\s+district|district)\s+([A-Za-z][A-Za-z\s-]{1,30})",
        r"जिल्ला\s*([^\s,।.]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            continue
        candidate = _normalize_district_text(match.group(1))
        if candidate:
            return candidate

    return None


def _normalize_district_text(value: str) -> str | None:
    cleaned = re.sub(r"\s+", " ", str(value).strip(" ,.;:"))
    if not cleaned:
        return None
    if len(cleaned) > 32:
        return None
    if re.search(r"\d", cleaned):
        return None
    stop_tokens = {"savings", "range", "business", "idea", "target", "district", "start", "want", "र", "बचत"}
    lowered = cleaned.lower()
    if lowered in stop_tokens:
        return None
    if any(token in lowered for token in ["lakh", "lakhs"]):
        return None
    if re.search(r"[A-Za-z]", cleaned):
        return " ".join(part.upper() if len(part) <= 3 and part.isupper() else part.capitalize() for part in cleaned.split())
    return cleaned


def _extract_current_location(text: str) -> str | None:
    stripped = text.strip()
    if not stripped:
        return None

    patterns = [
        r"\bi am in ([A-Za-z ]+?)(?:[,.]| and|$)",
        r"\bi'm in ([A-Za-z ]+?)(?:[,.]| and|$)",
        r"\bworking in ([A-Za-z ]+?)(?:[,.]| and|$)",
        r"\bfrom ([A-Za-z ]+?)(?:[,.]| and|$)",
        r"अहिले\s+([^\s।,.]+)\s*मा\s*छु",
        r"म\s+([^\s।,.]+)\s*मा\s*छु",
    ]
    for pattern in patterns:
        match = re.search(pattern, stripped, re.IGNORECASE)
        if match:
            candidate = match.group(1).strip(" .,")
            return candidate.title() if re.search(r"[A-Za-z]", candidate) else candidate

    simple_locations = ["Qatar", "Dubai", "Doha", "Saudi Arabia", "Kuwait", "Malaysia", "Abu Dhabi", "Oman"]
    lowered = stripped.lower()
    for location in simple_locations:
        if location.lower() in lowered:
            return location
    return None


def _is_small_talk_message(messages: list[dict[str, Any]] | None) -> bool:
    for message in reversed(messages or []):
        if message.get("role") != "user":
            continue
        raw = message.get("content", "").strip()
        return _is_small_talk_text(raw)
    return False


def _is_small_talk_text(text: str) -> bool:
    raw = text.strip()
    lowered = raw.lower()
    if not raw:
        return False
    if lowered in SMALL_TALK_PATTERNS["en"] or raw in SMALL_TALK_PATTERNS["ne"]:
        return True
    if len(lowered.split()) <= 2 and lowered in {"hi", "hello", "hey", "namaste"}:
        return True
    return False


def _normalize_freeform_location(text: str) -> str | None:
    cleaned = re.sub(r"\s+", " ", text.strip(" .,"))
    if not cleaned:
        return None
    if len(cleaned) > 40:
        return None
    if re.search(r"\d", cleaned):
        return None
    if any(token in cleaned.lower() for token in ["job", "business", "years", "worked", "experience", "skill"]):
        return None
    parts = [part.strip() for part in cleaned.split(",") if part.strip()]
    normalized_parts = []
    for part in parts:
        if part.isupper() and len(part) <= 4:
            normalized_parts.append(part)
        else:
            normalized_parts.append(part.title())
    return ", ".join(normalized_parts) if normalized_parts else None
