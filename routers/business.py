import copy

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from database import get_db
from models import BusinessChecklist, Profile
from schemas import APIResponse, ChecklistGenerateRequest, ChecklistResponse, ChecklistToggleRequest
from services.ai_service import generate_checklist

router = APIRouter(prefix="/business", tags=["business"])


@router.post("/checklist", response_model=APIResponse[ChecklistResponse])
def create_checklist(payload: ChecklistGenerateRequest, db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.id == payload.profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    existing = db.query(BusinessChecklist).filter(BusinessChecklist.profile_id == profile.id).first()
    if existing:
        return {"data": existing}

    generated = generate_checklist(profile)
    checklist = BusinessChecklist(
        profile_id=profile.id,
        trade=str(profile.trade_category.value if hasattr(profile.trade_category, "value") else profile.trade_category or "other"),
        district=profile.district_target or "Kathmandu",
        checklist_items=generated["checklist_items"],
        raw_ai_output=generated["raw_ai_output"],
    )
    db.add(checklist)
    db.commit()
    db.refresh(checklist)
    return {"data": checklist}


@router.get("/checklist/{profile_id}", response_model=APIResponse[ChecklistResponse])
def get_checklist(profile_id: str, db: Session = Depends(get_db)):
    checklist = db.query(BusinessChecklist).filter(BusinessChecklist.profile_id == profile_id).first()
    if not checklist:
        raise HTTPException(status_code=404, detail="Checklist not found")
    return {"data": checklist}


@router.patch("/checklist/item", response_model=APIResponse[ChecklistResponse])
def toggle_checklist_item(payload: ChecklistToggleRequest, db: Session = Depends(get_db)):
    checklist = db.query(BusinessChecklist).filter(BusinessChecklist.id == payload.checklist_id).first()
    if not checklist:
        raise HTTPException(status_code=404, detail="Checklist not found")
    if payload.item_index < 0 or payload.item_index >= len(checklist.checklist_items):
        raise HTTPException(status_code=400, detail="Checklist item index out of range")

    items = copy.deepcopy(list(checklist.checklist_items))
    items[payload.item_index]["done"] = payload.done
    checklist.checklist_items = items
    flag_modified(checklist, "checklist_items")
    db.add(checklist)
    db.commit()
    db.refresh(checklist)
    return {"data": checklist}
