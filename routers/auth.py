import uuid

from fastapi import APIRouter, Depends
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from models import Profile
from schemas import APIResponse, AuthSessionRequest, AuthSessionResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/session", response_model=APIResponse[AuthSessionResponse])
def create_auth_session(payload: AuthSessionRequest, db: Session = Depends(get_db)):
    profile = Profile(name=payload.name, phone=payload.phone)
    db.add(profile)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Phone number already exists")
    db.refresh(profile)
    return {"data": {"profile_id": profile.id, "token": f"dummy_token_{uuid.uuid4()}"}}
