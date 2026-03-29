import os
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Form
from fastapi.responses import Response
from sqlalchemy.orm import Session

from database import get_db
from models import ChatSession, Profile
from services.ai_service import get_welcome_message
from services.language_service import detect_language

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])

APP_URL = os.getenv("APP_URL", "https://farka-fe.vercel.app")


def _twiml(message: str) -> Response:
    # Escape XML special characters in message body
    safe = message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Message>{safe}</Message>
</Response>"""
    return Response(content=xml, media_type="text/xml")


@router.post("/webhook")
def whatsapp_webhook(
    From: str = Form(...),
    Body: str = Form(""),
    ProfileName: str = Form(""),
    db: Session = Depends(get_db),
):
    # "whatsapp:+9779812345678" → "9779812345678"
    raw_phone = From.replace("whatsapp:", "").replace("+", "").strip()
    name = ProfileName.strip() or "there"
    language = detect_language(Body) if Body.strip() else "en"

    # Returning user — look up by phone number
    profile = db.query(Profile).filter(Profile.phone == raw_phone).first()
    if profile:
        session = (
            db.query(ChatSession)
            .filter(ChatSession.profile_id == profile.id)
            .order_by(ChatSession.updated_at.desc())
            .first()
        )
        if session:
            link = f"{APP_URL}/chat?session_id={session.id}&from=whatsapp"
            if language == "ne":
                msg = (
                    f"फार्कामा फिर्ता स्वागत छ, {name}! 🙏\n\n"
                    f"तपाईंको यात्रा जारी राख्नुहोस्:\n{link}"
                )
            else:
                msg = (
                    f"Welcome back to FARKA, {name}! 🙏\n\n"
                    f"Continue your journey home:\n{link}"
                )
            return _twiml(msg)

    # New user — create a fresh session
    welcome = get_welcome_message(language)
    session = ChatSession(
        messages=[{"role": "assistant", "content": welcome, "timestamp": datetime.now(UTC).isoformat()}],
        workflow_stage="initial",
        language=language,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    link = f"{APP_URL}/chat?session_id={session.id}&from=whatsapp"

    if language == "ne":
        msg = (
            f"नमस्ते {name}! फार्कामा स्वागत छ 🇳🇵\n\n"
            f"हामी तपाईंलाई नेपाल फर्की जागिर खोज्न वा व्यवसाय सुरु गर्न मद्दत गर्छौं।\n\n"
            f"यहाँ आफ्नो यात्रा सुरु गर्नुहोस्:\n{link}"
        )
    else:
        msg = (
            f"Hi {name}! Welcome to FARKA 🇳🇵\n\n"
            f"We help Nepali workers like you find jobs or start a business back home.\n\n"
            f"Tap here to begin your journey:\n{link}"
        )

    return _twiml(msg)
