from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from models import ChatSession, Profile
from schemas import APIResponse, ChatMessageRequest, ChatMessageResponse, ChatStartResponse
from services.ai_service import get_welcome_message, process_message
from services.language_service import detect_language
from services.profile_service import has_meaningful_profile_data, sanitize_profile_updates

router = APIRouter(prefix="/chat", tags=["chat"])


def _chat_entry(role: str, content: str) -> dict:
    return {"role": role, "content": content, "timestamp": datetime.now(UTC).isoformat()}


@router.post("/start", response_model=APIResponse[ChatStartResponse])
def start_chat(db: Session = Depends(get_db)):
    message = get_welcome_message(language="en")
    session = ChatSession(messages=[_chat_entry("assistant", message)], workflow_stage="initial", language="en")
    db.add(session)
    db.commit()
    db.refresh(session)
    return {"data": {"session_id": session.id, "message": message, "stage": "initial"}}


@router.post("/message", response_model=APIResponse[ChatMessageResponse])
def chat_message(payload: ChatMessageRequest, db: Session = Depends(get_db)):
    session = db.query(ChatSession).filter(ChatSession.id == payload.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    messages = list(session.messages or [])
    messages.append(_chat_entry("user", payload.content))
    session.messages = messages

    current_stage = session.workflow_stage.value if hasattr(session.workflow_stage, "value") else str(session.workflow_stage)
    if current_stage == "initial":
        language = detect_language(payload.content)
        session.language = language
        session.workflow_stage = "language_set"

    result = process_message(session, payload.content)
    session.workflow_stage = result["next_stage"]
    session.updated_at = datetime.now(UTC)
    session.messages = list(session.messages or []) + [_chat_entry("assistant", result["reply"])]

    extracted_data = sanitize_profile_updates(result.get("extracted_data", {}))
    if extracted_data and has_meaningful_profile_data(extracted_data):
        if session.profile_id:
            profile = db.query(Profile).filter(Profile.id == session.profile_id).first()
        else:
            profile = Profile(language_pref=session.language)
            db.add(profile)
            db.flush()
            session.profile_id = profile.id

        for key, value in extracted_data.items():
            if hasattr(profile, key) and value is not None:
                setattr(profile, key, value)
        profile.language_pref = session.language
        db.add(profile)

    db.add(session)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Phone number already exists")
    db.refresh(session)

    return {
        "data": {
            "message": result["reply"],
            "stage": session.workflow_stage.value if hasattr(session.workflow_stage, "value") else str(session.workflow_stage),
            "profile_id": session.profile_id,
            "redirect": result.get("redirect"),
        }
    }
