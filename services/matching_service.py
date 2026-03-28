from models import Job, Profile


def compute_matches(profile: Profile, jobs: list[Job]) -> list[dict]:
    profile_skills = set(profile.skills or [])
    results = []

    for job in jobs:
        score = 0.0
        matched_tags = sorted(profile_skills.intersection(set(job.skill_tags or [])))

        if job.trade_category == profile.trade_category:
            score += 0.40
        if profile.district_target and job.district == profile.district_target:
            score += 0.15

        score += min(len(matched_tags) * 0.10, 0.25)

        experience = profile.years_experience or 0
        if experience >= 3 and job.experience_level in ["mid", "senior"]:
            score += 0.10
        if experience >= 6 and job.experience_level == "senior":
            score += 0.10

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
