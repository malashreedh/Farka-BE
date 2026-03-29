import copy

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from database import get_db
from models import BusinessChecklist, Profile
from schemas import (
    APIResponse,
    BusinessViabilityRequest,
    BusinessViabilityResponse,
    ChecklistGenerateRequest,
    ChecklistResponse,
    ChecklistToggleRequest,
)
from services.ai_service import generate_checklist, generate_viability_notes
from services.business_viability_service import build_viability_options, infer_savings_amount_npr

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


@router.post("/viability", response_model=APIResponse[BusinessViabilityResponse])
def business_viability(payload: BusinessViabilityRequest, db: Session = Depends(get_db)):
    profile = None
    if payload.profile_id:
        profile = db.query(Profile).filter(Profile.id == payload.profile_id).first()
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")

    trade_category = payload.trade_category or (
        str(profile.trade_category.value if hasattr(profile.trade_category, "value") else profile.trade_category)
        if profile and getattr(profile, "trade_category", None)
        else None
    )
    district = payload.district or (profile.district_target if profile else None) or "Kathmandu"
    savings_amount_npr = payload.savings_amount_npr or infer_savings_amount_npr(profile)

    if not trade_category:
        raise HTTPException(status_code=400, detail="Trade category is required")

    options = build_viability_options(trade_category, district, savings_amount_npr)
    notes = generate_viability_notes(trade_category, district, savings_amount_npr, options)
    for option, note in zip(options, notes, strict=False):
        option["ai_note"] = note

    return {
        "data": {
            "trade_category": trade_category,
            "district": district,
            "savings_amount_npr": savings_amount_npr,
            "options": options,
        }
    }
