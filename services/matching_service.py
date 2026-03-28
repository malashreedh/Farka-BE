from models import Job, Profile


def compute_matches(profile: Profile, jobs: list[Job]) -> list[dict]:
    profile_skills = {str(skill).strip().lower() for skill in (profile.skills or []) if str(skill).strip()}
    results = []

    for job in jobs:
        score = 0.0
        job_tags = {str(tag).strip().lower() for tag in (job.skill_tags or []) if str(tag).strip()}
        matched_tags = sorted(profile_skills.intersection(job_tags))

        if job.trade_category == profile.trade_category:
            score += 0.45
        if profile.district_target and job.district == profile.district_target:
            score += 0.10

        score += min(len(matched_tags) * 0.12, 0.30)

        experience = profile.years_experience or 0
        if experience >= 2 and job.experience_level in ["mid", "senior"]:
            score += 0.10
        if experience >= 6 and job.experience_level == "senior":
            score += 0.10
        if experience <= 2 and job.experience_level == "entry":
            score += 0.08

        score = round(min(score, 1.0), 2)
        if score >= 0.2:
            results.append(
                {
                    "job_id": job.id,
                    "match_score": score,
                    "matched_tags": matched_tags,
                }
            )

    results.sort(key=lambda item: item["match_score"], reverse=True)
    return results[:15]
