import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import SessionLocal, init_db
from routers import auth, business, chat, jobs, profile, whatsapp
from seed_jobs import seed

app = FastAPI(title="FARKA API")


def _get_cors_origins() -> list[str]:
    raw_origins = os.getenv("CORS_ORIGINS") or os.getenv("CORS_ORIGIN") or "http://localhost:3000"
    return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]


cors_origins = _get_cors_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(profile.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1")
app.include_router(business.router, prefix="/api/v1")
app.include_router(whatsapp.router, prefix="/api/v1")


@app.on_event("startup")
def startup_event():
    init_db()
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()


@app.get("/")
def health():
    return {"data": {"status": "ok"}, "message": "success"}
