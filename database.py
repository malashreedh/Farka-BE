import os
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()


def _require_database_url() -> str:
    raw_url = os.getenv("DATABASE_URL", "").strip()
    if not raw_url:
        raise RuntimeError("DATABASE_URL is required. Set it to your Supabase Postgres connection string.")
    return raw_url


def _normalize_database_url(raw_url: str) -> str:
    if raw_url.startswith("postgres://"):
        raw_url = raw_url.replace("postgres://", "postgresql://", 1)

    parsed = urlparse(raw_url)
    if not parsed.scheme.startswith("postgres"):
        raise RuntimeError("Unsupported DATABASE_URL scheme. FARKA requires a Postgres/Supabase connection string.")

    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    host = parsed.hostname or ""

    if "supabase.co" in host and "sslmode" not in query:
        query["sslmode"] = "require"

    if "connect_timeout" not in query:
        query["connect_timeout"] = "10"

    return urlunparse(parsed._replace(query=urlencode(query)))


DATABASE_URL = _normalize_database_url(_require_database_url())

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from models import Base as ModelsBase

    ModelsBase.metadata.create_all(bind=engine)
