import os
import io
import json
import re
from openai import OpenAI
from gtts import gTTS
from .language_service import get_language_instruction

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ── Canonical skill tags (must match seed data exactly) ──────────────────────
SKILL_TAGS = {
    "construction":  ["formwork","concrete pouring","site supervision","scaffolding","MEP works","safety management","equipment operation","masonry","plumbing","electrical fitting"],
    "hospitality":   ["front desk","housekeeping","food service","kitchen prep","event management","bartending","guest relations","hotel operations","tour guiding","cleaning supervision"],
    "manufacturing": ["machine operation","quality control","assembly line","welding","fabrication","inventory management","forklift operation","production planning","packaging"],
    "agriculture":   ["crop management","irrigation","livestock","greenhouse","organic farming","harvesting","agri-machinery","soil testing","pest control","market selling"],
    "transport":     ["heavy vehicle driving","logistics","route planning","vehicle maintenance","cargo handling","fleet management","customer service","GPS navigation"],
    "tech":          ["web development","data entry","IT support","networking","social media","graphic design","video editing","mobile apps","customer support","digital marketing"],
    "domestic":      ["childcare","elder care","cooking","cleaning","home management","tutoring","driving","security","laundry","event catering"],
}

# ── Stage goals injected into the system prompt ───────────────────────────────
STAGE_GOALS = {
    "initial":                    "Greet the user warmly. Ask them to tell you where they are right now.",
    "language_set":               "Ask where they are now and what work they did abroad. Be warm and curious.",
    "collecting_basics":          "Extract current_location and trade_category. Once you have both, ask about their years of experience.",
    "collecting_experience":      "Extract years_experience. Then ask whether they want a job when they return or want to start their own business.",
    "path_decision":              "Determine if they want to be a job_seeker or business_starter. Ask clearly: 'Are you looking for a job when you return, or do you want to start your own business?'",
    "collecting_skills":          "Present skill tag suggestions for their trade. Ask which tags apply to them. Extract confirmed skills as a list.",
    "collecting_business_details":"Ask which district they want to return to, their savings range (under_5L / 5L_to_20L / 20L_to_50L / above_50L), and their specific business idea. Be encouraging.",
    "profile_complete":           "Tell the user their profile is complete and you are now finding matches or generating their plan.",
    "job_matching":               "Tell the user you are finding the best job matches for them.",
    "checklist_generated":        "Tell the user their business checklist is ready.",
}

# ── Fallback checklist used when GPT call fails ───────────────────────────────
FALLBACK_CHECKLIST = [
    {"category": "Legal & Registration", "week": 1, "task": "Gather citizenship certificate and prepare copies of required documents", "done": False},
    {"category": "Legal & Registration", "week": 1, "task": "Register business at local Ward Office", "done": False},
    {"category": "Legal & Registration", "week": 1, "task": "Apply for PAN registration at the Inland Revenue Office", "done": False},
    {"category": "Finance & Loans",      "week": 2, "task": "Open a dedicated business bank account at a local commercial bank", "done": False},
    {"category": "Finance & Loans",      "week": 2, "task": "Research Youth Self-Employment Fund (YSEF) loan eligibility and apply", "done": False},
    {"category": "Finance & Loans",      "week": 2, "task": "Contact Agriculture Development Bank or Grameen Bikas Bank for micro-loan options", "done": False},
    {"category": "Location & Equipment", "week": 3, "task": "Scout and finalise a suitable business location or land in the target district", "done": False},
    {"category": "Location & Equipment", "week": 3, "task": "Purchase or rent the required tools and equipment for the business", "done": False},
    {"category": "Marketing",            "week": 4, "task": "Create a Facebook page and TikTok account for local marketing", "done": False},
    {"category": "Operations",           "week": 5, "task": "Hire or train your first employee or apprentice through a local network", "done": False},
]


# ── Public API ────────────────────────────────────────────────────────────────

def get_welcome_message(language: str) -> str:
    """Return the static welcome message in the correct language."""
    if language == "ne":
        return (
            "नमस्ते! म FARKA हुँ। म विदेशमा काम गर्ने नेपालीहरूलाई घर फर्कने बाटो "
            "खोज्न मद्दत गर्छु। पहिले भन्नुस् — अहिले तपाईं कहाँ हुनुहुन्छ?"
        )
    return (
        "Namaste! I'm FARKA. I help Nepali workers abroad find their path back home — "
        "whether that's a job or starting a business. "
        "First, tell me: where are you right now?"
    )


def process_message(session, user_message: str) -> dict:
    """
    Core chat processing function.

    Args:
        session: ChatSession ORM object (workflow_stage, messages, language, profile).
        user_message: Latest message text from the user.

    Returns:
        {
            "reply":          str   — user-facing bot message,
            "extracted_data": dict  — profile fields extracted from this turn,
            "next_stage":     str   — new workflow stage,
            "redirect":       str | None  — "jobs", "checklist", or None,
        }
    """
    stage    = session.workflow_stage or "initial"
    language = session.language or "en"

    # Fetch trade category from linked profile if available
    trade_category = None
    if hasattr(session, "profile") and session.profile:
        trade_category = getattr(session.profile, "trade_category", None)

    system_prompt = _build_system_prompt(stage, language, trade_category)

    # Build message list — include last 6 history turns for context
    messages = [{"role": "system", "content": system_prompt}]
    for msg in (session.messages or [])[-6:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.7,
            max_tokens=800,
        )
        raw_response = response.choices[0].message.content or ""
    except Exception as exc:
        print(f"[ai_service] OpenAI error: {exc}")
        return {
            "reply":          "I'm having a little trouble connecting right now. Please try again in a moment.",
            "extracted_data": {},
            "next_stage":     stage,
            "redirect":       None,
        }

    clean_reply, extracted_data = _parse_extract(raw_response)

    next_stage = extracted_data.pop("next_stage", stage)
    redirect   = extracted_data.pop("redirect",    None)

    # Resolve profile_complete → actual terminal stage using path info
    if next_stage == "profile_complete":
        path = _resolve_path(session, extracted_data)
        if path == "job_seeker":
            next_stage = "job_matching"
            redirect   = "jobs"
        elif path == "business_starter":
            next_stage = "checklist_generated"
            redirect   = "checklist"

    # Safety net: ensure redirect matches terminal stage
    if next_stage == "job_matching" and redirect is None:
        redirect = "jobs"
    if next_stage == "checklist_generated" and redirect is None:
        redirect = "checklist"

    return {
        "reply":          clean_reply,
        "extracted_data": extracted_data,
        "next_stage":     next_stage,
        "redirect":       redirect,
    }


def generate_checklist(profile) -> tuple:
    """
    Generate an 8-week business launch checklist via GPT-4o.

    Args:
        profile: Profile ORM object.

    Returns:
        (checklist_items: list[dict], raw_ai_output: str)
    """
    language    = getattr(profile, "language_pref", "en") or "en"
    trade       = getattr(profile, "trade_category", "general") or "general"
    district    = getattr(profile, "district_target", "Kathmandu") or "Kathmandu"
    savings     = getattr(profile, "savings_range",   "under_5L")  or "under_5L"
    skills      = getattr(profile, "skills", []) or []

    business_idea = f"{trade} business"
    if skills:
        business_idea = f"{trade} business using skills: {', '.join(skills[:5])}"

    lang_instruction = get_language_instruction(language)

    system_prompt = (
        "You are a business advisor for Nepal. Generate a realistic 8-week business launch checklist "
        "for a returning Nepali migrant worker. Be specific to Nepal — use real government offices, "
        "real document names, and real loan schemes (YSEF, Agriculture Development Bank, "
        "Grameen Bikas Bank, etc.). Output ONLY a valid JSON array with no markdown or extra text.\n"
        f"{lang_instruction}"
    )

    user_prompt = (
        f"Worker profile: Trade={trade}, Target district={district}, "
        f"Savings={savings}, Business idea: {business_idea}.\n\n"
        "Generate a checklist as a JSON array using exactly this schema:\n"
        '[{"category": "Legal & Registration", "week": 1, "task": "...", "done": false}]\n\n'
        "Spread tasks across 8 weeks. Use these categories: "
        "Legal & Registration, Finance & Loans, Location & Equipment, Marketing, Operations. "
        "Generate at least 15 tasks total. Make each task highly specific to Nepal, "
        "the district, and the trade.\nOutput ONLY the JSON array."
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


def _parse_extract(response_text: str) -> tuple[str, dict[str, Any]]:
    match = EXTRACT_PATTERN.search(response_text or "")
    if not match:
        return response_text.strip(), {}
    extract_text = match.group(1).strip()
    reply = EXTRACT_PATTERN.sub("", response_text).strip()
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=0.5,
            max_tokens=2000,
        )
        raw_output = (response.choices[0].message.content or "").strip()

        # Strip markdown code fences if present
        raw_output = re.sub(r'^```(?:json)?\s*', '', raw_output)
        raw_output = re.sub(r'\s*```$',          '', raw_output)

        items = json.loads(raw_output)
        validated = [
            {
                "category": str(item.get("category", "Operations")),
                "week":     int(item.get("week", 1)),
                "task":     str(item.get("task", "")),
                "done":     bool(item.get("done", False)),
            }
            for item in items
        ]
        return validated, raw_output

    except Exception as exc:
        print(f"[ai_service] Checklist generation error: {exc}")
        return FALLBACK_CHECKLIST, f"Fallback used — error: {exc}"


def transcribe_audio(audio_file) -> str:
    """
    Transcribe an audio file to text using OpenAI Whisper.
    Supports both English and Nepali speech.

    Args:
        audio_file: File-like object (e.g. from FastAPI UploadFile.file).

    Returns:
        Transcribed text string.
    """
    try:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
        )
        return transcript.text
    except Exception as exc:
        print(f"[ai_service] Whisper transcription error: {exc}")
        return ""


def synthesize_speech(text: str, language: str) -> bytes:
    """
    Convert text to speech audio using gTTS.
    Supports English ("en") and Nepali ("ne").

    Args:
        text:     The text to convert to speech.
        language: "en" or "ne".

    Returns:
        MP3 audio as bytes. Returns empty bytes if synthesis fails.
    """
    gtts_lang = "ne" if language == "ne" else "en"
    try:
        tts = gTTS(text=text, lang=gtts_lang, slow=False)
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        return audio_buffer.read()
    except Exception as exc:
        print(f"[ai_service] gTTS synthesis error: {exc}")
        return b""


# ── Private helpers ───────────────────────────────────────────────────────────

def _build_system_prompt(stage: str, language: str, trade_category: str | None) -> str:
    lang_instruction = get_language_instruction(language)
    stage_goal = STAGE_GOALS.get(stage, "Continue the conversation helpfully.")

    skill_hint = ""
    if stage == "collecting_skills" and trade_category in SKILL_TAGS:
        tags = SKILL_TAGS[trade_category]
        skill_hint = (
            f"\nAvailable skill tags for {trade_category}: {json.dumps(tags)}\n"
            "Present these as options and ask the user to confirm which apply to them."
        )

    return f"""You are FARKA, a warm and helpful career and business advisor for Nepali migrant workers returning home.
{lang_instruction}
Current workflow stage: {stage}
Your goal at this stage: {stage_goal}{skill_hint}

At the end of every response you MUST output a JSON block wrapped in <extract></extract> tags.
Extract any profile data the user has shared, plus the next_stage and redirect fields.

Extractable profile fields:
  name            (string, optional)
  current_location (string)
  trade_category  (one of: construction, hospitality, manufacturing, agriculture, domestic, transport, tech, other)
  years_experience (integer)
  path            (one of: job_seeker, business_starter)
  skills          (list of strings — use canonical tag strings only)
  district_target (string, a real district in Nepal)
  has_savings     (boolean)
  savings_range   (one of: under_5L, 5L_to_20L, 20L_to_50L, above_50L)

Required fields in every extract block:
  next_stage  (string — the stage to transition to after this turn)
  redirect    (null | "jobs" | "checklist")

Stage transition rules:
  language_set              → collecting_basics         (once location + trade known)
  collecting_basics         → collecting_experience     (once location + trade extracted)
  collecting_experience     → path_decision             (once years_experience extracted)
  path_decision             → collecting_skills         (if path = job_seeker)
  path_decision             → collecting_business_details (if path = business_starter)
  collecting_skills         → profile_complete  + redirect="jobs"      (once skills confirmed)
  collecting_business_details → profile_complete + redirect="checklist" (once district+savings+idea collected)

Only advance the stage when the required data has actually been collected.
If nothing new was extracted, repeat the current stage in next_stage.

Example extract: <extract>{{"trade_category": "construction", "years_experience": 5, "next_stage": "path_decision", "redirect": null}}</extract>
Empty extract:   <extract>{{"next_stage": "{stage}", "redirect": null}}</extract>
"""


def _parse_extract(raw_response: str) -> tuple[str, dict]:
    """Split GPT output into (clean_reply, extracted_data dict)."""
    pattern = re.compile(r'<extract>(.*?)</extract>', re.DOTALL)
    match = pattern.search(raw_response)

    extracted_data: dict = {}
    if match:
        try:
            extracted_data = json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            extracted_data = {}

    clean_reply = pattern.sub('', raw_response).strip()
    return clean_reply, extracted_data


def _resolve_path(session, extracted_data: dict) -> str | None:
    """Determine the user's chosen path from session profile or extracted data."""
    # Check profile attached to session
    if hasattr(session, "profile") and session.profile:
        path = getattr(session.profile, "path", None)
        if path in ("job_seeker", "business_starter"):
            return path

    # Fall back to what was just extracted this turn
    return extracted_data.get("path")
