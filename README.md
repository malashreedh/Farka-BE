# FARKA Backend

FastAPI backend for the FARKA hackathon MVP.

## Run locally

1. Create a virtual environment.
2. Install dependencies:
   `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and set values if needed.
4. Start the server:
   `uvicorn main:app --reload`

Default local development uses `sqlite:///./farka_dev.db` if `DATABASE_URL` is not set.
For shared environments, point `DATABASE_URL` to local Postgres or Supabase Postgres.

## API

- `POST /api/v1/chat/start`
- `POST /api/v1/chat/message`
- `GET /api/v1/profile/{id}`
- `PATCH /api/v1/profile/{id}`
- `GET /api/v1/jobs`
- `POST /api/v1/jobs/match`
- `GET /api/v1/jobs/matches/{profile_id}`
- `POST /api/v1/business/checklist`
- `GET /api/v1/business/checklist/{profile_id}`
- `PATCH /api/v1/business/checklist/item`
- `POST /api/v1/auth/session`

## Notes

- OpenAI is optional for local development. If no `OPENAI_API_KEY` is set, the app uses deterministic fallback chat and checklist logic.
- Job seeds are created automatically at startup when the jobs table is empty.
