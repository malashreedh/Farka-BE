# FARKA — Backend

FARKA is a chat-first platform for Nepali migrant workers abroad (or returning home) who want to know: **"Is there actually something for me back in Nepal?"**

The chat builds a user profile through conversation, then routes them to one of two paths:
- **Path A — Job Seeker:** find real jobs matching their skills
- **Path B — Business Starter:** get an AI-generated 8-week checklist to launch their own venture

Both English and Nepali (Devanagari) are fully supported — language is auto-detected from the user's first message.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python 3.11) |
| Database | PostgreSQL + SQLAlchemy (sync) + Alembic |
| AI / Chat | OpenAI GPT-4o mini (chat logic) + Whisper (voice transcription) |
| Voice | OpenAI Whisper (speech-to-text) + ElevenLabs / gTTS fallback (text-to-speech) |
| Auth | Dummy JWT — no real verification (MVP) |

---

## Project Structure

```
farka-backend/
├── main.py                      # FastAPI app, CORS, router registration, startup
├── database.py                  # SQLAlchemy engine, session, init_db()
├── models.py                    # ORM models: profiles, chat_sessions, jobs, job_matches, business_checklists
├── schemas.py                   # Pydantic v2 request/response schemas
├── seed_jobs.py                 # Seeds 40+ realistic jobs into the DB on startup
├── requirements.txt
├── .env                         # Local secrets (not committed)
├── .env.example                 # Template for .env
├── routers/
│   ├── auth.py                  # POST /auth/session — dummy auth
│   ├── chat.py                  # POST /chat/start, /chat/message, /chat/voice-message
│   ├── profile.py               # GET/PATCH /profile/{id}
│   ├── jobs.py                  # GET /jobs, POST /jobs/match, GET /jobs/matches/{profile_id}
│   └── business.py              # POST/GET /business/checklist, PATCH /business/checklist/item
├── services/
│   ├── ai_service.py            # GPT-4o chat logic, Whisper transcription, ElevenLabs/gTTS voice synthesis, checklist generation
│   ├── language_service.py      # Language detection (en/ne) + LLM language instructions
│   ├── matching_service.py      # Job matching algorithm (skill tag scoring)
│   ├── business_viability_service.py # Startup cost, break-even, and risk estimation
│   └── profile_service.py       # Profile creation/update helpers
└── tests/
    └── test_app.py              # Integration tests for full chat flows
```

---

## Prerequisites

- Python 3.11+
- Postgres-compatible database URL (Supabase recommended)
- OpenAI API key with credits (GPT-4o mini + Whisper)
- Optional ElevenLabs API key for higher-quality TTS

---

## Setup & Running Locally

### 1. Clone and enter the directory
```bash
git clone https://github.com/malashreedh/Farka-BE.git
cd Farka-BE
```

### 2. Create and activate a virtual environment
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Create your `.env` file
```bash
cp .env.example .env
```
Then open `.env` and fill in:
```
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://postgres.[YOUR_PROJECT_REF]:[YOUR_PASSWORD]@aws-1-us-east-1.pooler.supabase.com:5432/postgres?sslmode=require
ELEVENLABS_API_KEY=
```

### 5. Start the server
```bash
uvicorn main:app --reload
```

Server runs at: `http://localhost:8000`
Interactive API docs: `http://localhost:8000/docs`

> Job seed data (40+ jobs) is inserted automatically on first startup if the jobs table is empty.

---

## API Endpoints

All endpoints are prefixed with `/api/v1`. All responses follow this format:
- **Success:** `{"data": <payload>, "message": "success"}`
- **Error:** `{"detail": "error message"}`

### Auth
| Method | Endpoint | Body | Description |
|---|---|---|---|
| POST | `/auth/session` | `{name?, phone?}` | Create profile, return dummy token |

### Chat
| Method | Endpoint | Body | Description |
|---|---|---|---|
| POST | `/chat/start` | `{}` | Start a new chat session, get welcome message |
| POST | `/chat/message` | `{session_id, content}` | Send a text message, advance workflow stage |
| POST | `/chat/voice-message` | `form: session_id + audio file` | Send a voice message, get text + audio reply |

### Profile
| Method | Endpoint | Description |
|---|---|---|
| GET | `/profile/{id}` | Get profile by ID |
| PATCH | `/profile/{id}` | Update profile fields |

### Jobs
| Method | Endpoint | Description |
|---|---|---|
| GET | `/jobs` | List jobs (filter by trade_category, district, experience_level) |
| GET | `/jobs/density` | Aggregate job counts by district and trade category for map visualisation |
| POST | `/jobs/match` | Compute and save job matches for a profile |
| GET | `/jobs/matches/{profile_id}` | Get saved job matches sorted by score |

### Business
| Method | Endpoint | Description |
|---|---|---|
| POST | `/business/checklist` | Generate AI checklist for a profile |
| POST | `/business/viability` | Estimate startup cost, break-even timeline, and risk for 3 business options |
| GET | `/business/checklist/{profile_id}` | Get existing checklist |
| PATCH | `/business/checklist/item` | Toggle a checklist item done/undone |

---

## Chat Workflow

The chat progresses through these stages automatically:

```
initial
  └── language detected (en/ne from first message)
        └── language_set
              └── collecting_basics       (location + trade)
                    └── collecting_experience    (years of experience)
                          └── path_decision      (job or business?)
                                ├── collecting_skills          → job_matching   → /results/jobs
                                └── collecting_business_details → checklist_generated → /results/business
```

Stage transitions are driven entirely by GPT-4o — the model extracts profile data and determines when enough information has been collected to advance.

---

## Voice Chat

Voice support is built on two functions in `services/ai_service.py`:

- **`transcribe_audio(audio_file)`** — Uses OpenAI Whisper to transcribe speech to text. Supports both English and Nepali speech automatically.
- **`synthesize_speech(text, language)`** — Uses ElevenLabs when configured, otherwise falls back to gTTS. Passes `"ne"` for Nepali, `"en"` for English.

The voice endpoint (`POST /chat/voice-message`) accepts an audio file, transcribes it, runs it through the same `process_message()` logic as text chat, and returns both a text reply and MP3 audio (base64 encoded).

---

## Business Viability

`POST /business/viability` estimates three business paths for a returnee using:
- trade-specific startup templates
- district cost multipliers
- available savings
- GPT-generated practical notes for each option

Each option includes startup cost, working capital, savings gap, break-even months, monthly revenue/cost ranges, risk level, and suggested first steps.

---

## Language Support

Language is auto-detected from the user's first message by scanning for Nepali Devanagari unicode characters (`\u0900–\u097F`). If more than 2 are found, the session is set to Nepali (`ne`), otherwise English (`en`).

All GPT-4o prompts include a language instruction that forces the model to respond in the detected language. gTTS synthesis also switches to Nepali voice when `language="ne"`.

---

## Running Tests

```bash
pytest tests/test_app.py -v
```

Tests cover the full job seeker flow, business starter flow, checklist generation, and checklist item toggling.

---

## Team

| Person | Role | Owns |
|---|---|---|
| Person 1 | Backend Lead | `main.py`, `database.py`, `models.py`, `schemas.py`, `routers/` |
| Person 2 | Frontend Lead | `farka-frontend/` (Next.js 14) |
| Person 3 | AI / Chat Engineer | `services/ai_service.py`, `services/language_service.py` |
| Person 4 | Data Engineer | `services/matching_service.py`, `seed_jobs.py` |
| Person 5 | Integration + Pitch | End-to-end testing, demo, presentation |

---

## Nepal-US Hackathon 2026
