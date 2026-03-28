from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from models import Profile
from schemas import APIResponse, ProfileResponse, ProfileUpdate
from services.profile_service import sanitize_profile_updates

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/{profile_id}", response_model=APIResponse[ProfileResponse])
def get_profile(profile_id: str, db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"data": profile}


@router.patch("/{profile_id}", response_model=APIResponse[ProfileResponse])
def update_profile(profile_id: str, payload: ProfileUpdate, db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    for key, value in sanitize_profile_updates(payload.model_dump(exclude_unset=True)).items():
        setattr(profile, key, value)

    db.add(profile)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Phone number already exists")
    db.refresh(profile)
    return {"data": profile}
