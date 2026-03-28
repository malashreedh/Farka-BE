from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models import Job, JobMatch, Profile
from schemas import APIResponse, JobMatchRequest, JobMatchResponse, JobResponse
from services.matching_service import compute_matches

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=APIResponse[list[JobResponse]])
def list_jobs(
    trade_category: str | None = None,
    district: str | None = None,
    experience_level: str | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    query = db.query(Job).filter(Job.is_active.is_(True))
    if trade_category:
        query = query.filter(Job.trade_category == trade_category)
    if district:
        query = query.filter(Job.district == district)
    if experience_level:
        query = query.filter(Job.experience_level == experience_level)

    jobs = query.offset((page - 1) * limit).limit(limit).all()
    return {"data": jobs}


@router.post("/match", response_model=APIResponse[list[JobMatchResponse]])
def match_jobs(payload: JobMatchRequest, db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.id == payload.profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    jobs = db.query(Job).filter(Job.is_active.is_(True)).all()
    matches = compute_matches(profile, jobs)
    db.query(JobMatch).filter(JobMatch.profile_id == profile.id).delete()

    job_by_id = {job.id: job for job in jobs}
    response_data = []
    for match in matches[:10]:
        record = JobMatch(
            profile_id=profile.id,
            job_id=match["job_id"],
            match_score=match["match_score"],
            matched_tags=match["matched_tags"],
        )
        db.add(record)
        response_data.append(
            {
                "job": job_by_id[match["job_id"]],
                "match_score": match["match_score"],
                "matched_tags": match["matched_tags"],
            }
        )

    db.commit()
    return {"data": response_data}


@router.get("/matches/{profile_id}", response_model=APIResponse[list[JobMatchResponse]])
def get_saved_matches(profile_id: str, db: Session = Depends(get_db)):
    matches = (
        db.query(JobMatch)
        .options(joinedload(JobMatch.job))
        .filter(JobMatch.profile_id == profile_id)
        .order_by(JobMatch.match_score.desc())
        .all()
    )
    data = [
        {"job": match.job, "match_score": match.match_score, "matched_tags": match.matched_tags}
        for match in matches
        if match.job
    ]
    return {"data": data}
