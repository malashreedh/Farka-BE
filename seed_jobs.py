from __future__ import annotations

from sqlalchemy.orm import Session

from models import Job


def seed(db: Session) -> None:
    jobs = _jobs()
    existing = {(job.title, job.org_name): job for job in db.query(Job).all()}

    for payload in jobs:
        key = (payload["title"], payload["org_name"])
        if key in existing:
            job = existing[key]
            for field, value in payload.items():
                setattr(job, field, value)
            db.add(job)
        else:
            db.add(Job(**payload))

    db.commit()


def _jobs() -> list[dict]:
    base_jobs = [
        {"title": "Junior Site Supervisor", "org_name": "Department of Roads", "org_type": "government", "district": "Kathmandu", "trade_category": "construction", "skill_tags": ["site supervision", "safety management", "masonry"], "experience_level": "entry", "salary_range": "Rs 32,000 – Rs 45,000"},
        {"title": "Civil Works Officer", "org_name": "Nepal Army Engineering", "org_type": "government", "district": "Lalitpur", "trade_category": "construction", "skill_tags": ["formwork", "concrete pouring", "site supervision"], "experience_level": "mid", "salary_range": "Rs 45,000 – Rs 68,000"},
        {"title": "Water Supply Technician", "org_name": "DWSS", "org_type": "government", "district": "Bhaktapur", "trade_category": "construction", "skill_tags": ["plumbing", "electrical fitting", "safety management"], "experience_level": "mid", "salary_range": "Rs 38,000 – Rs 60,000"},
        {"title": "Agriculture Program Assistant", "org_name": "Ministry of Agriculture", "org_type": "government", "district": "Chitwan", "trade_category": "agriculture", "skill_tags": ["crop management", "soil testing", "market selling"], "experience_level": "entry", "salary_range": "Rs 30,000 – Rs 42,000"},
        {"title": "Network Support Associate", "org_name": "Nepal Telecom", "org_type": "government", "district": "Kathmandu", "trade_category": "tech", "skill_tags": ["networking", "IT support", "customer support"], "experience_level": "mid", "salary_range": "Rs 40,000 – Rs 65,000"},
        {"title": "Municipal Hospitality Coordinator", "org_name": "Pokhara Local Municipality", "org_type": "government", "district": "Pokhara", "trade_category": "hospitality", "skill_tags": ["guest relations", "event management", "tour guiding"], "experience_level": "mid", "salary_range": "Rs 35,000 – Rs 52,000"},
        {"title": "Electrical Maintenance Officer", "org_name": "Nepal Electricity Authority", "org_type": "government", "district": "Butwal", "trade_category": "construction", "skill_tags": ["electrical fitting", "equipment operation", "safety management"], "experience_level": "senior", "salary_range": "Rs 55,000 – Rs 82,000"},
        {"title": "Fleet Operations Assistant", "org_name": "Department of Transport", "org_type": "government", "district": "Biratnagar", "trade_category": "transport", "skill_tags": ["logistics", "route planning", "vehicle maintenance"], "experience_level": "entry", "salary_range": "Rs 28,000 – Rs 40,000"},
        {"title": "Irrigation Field Supervisor", "org_name": "Ministry of Agriculture", "org_type": "government", "district": "Chitwan", "trade_category": "agriculture", "skill_tags": ["irrigation", "crop management", "agri-machinery"], "experience_level": "mid", "salary_range": "Rs 40,000 – Rs 58,000"},
        {"title": "Public Works Masonry Trainer", "org_name": "Bhaktapur Municipality", "org_type": "government", "district": "Bhaktapur", "trade_category": "construction", "skill_tags": ["masonry", "site supervision", "safety management"], "experience_level": "senior", "salary_range": "Rs 48,000 – Rs 70,000"},
        {"title": "Assistant Project Engineer", "org_name": "Khimti Nirman", "org_type": "private", "district": "Kathmandu", "trade_category": "construction", "skill_tags": ["formwork", "concrete pouring", "site supervision", "safety management"], "experience_level": "mid", "salary_range": "Rs 42,000 – Rs 63,000"},
        {"title": "Scaffolding Supervisor", "org_name": "CG Construction", "org_type": "private", "district": "Lalitpur", "trade_category": "construction", "skill_tags": ["scaffolding", "safety management", "equipment operation"], "experience_level": "senior", "salary_range": "Rs 50,000 – Rs 76,000"},
        {"title": "MEP Site Coordinator", "org_name": "Kalika Construction", "org_type": "private", "district": "Pokhara", "trade_category": "construction", "skill_tags": ["MEP works", "plumbing", "electrical fitting"], "experience_level": "mid", "salary_range": "Rs 46,000 – Rs 67,000"},
        {"title": "Guest Relations Officer", "org_name": "Hotel Annapurna", "org_type": "private", "district": "Kathmandu", "trade_category": "hospitality", "skill_tags": ["guest relations", "front desk", "hotel operations"], "experience_level": "mid", "salary_range": "Rs 33,000 – Rs 50,000"},
        {"title": "Housekeeping Lead", "org_name": "Hyatt Regency Kathmandu", "org_type": "private", "district": "Kathmandu", "trade_category": "hospitality", "skill_tags": ["housekeeping", "cleaning supervision", "guest relations"], "experience_level": "senior", "salary_range": "Rs 40,000 – Rs 62,000"},
        {"title": "Food Service Associate", "org_name": "Summit Hotels", "org_type": "private", "district": "Pokhara", "trade_category": "hospitality", "skill_tags": ["food service", "kitchen prep", "guest relations"], "experience_level": "entry", "salary_range": "Rs 26,000 – Rs 38,000"},
        {"title": "Fleet Scheduler", "org_name": "Sajha Yatayat", "org_type": "private", "district": "Lalitpur", "trade_category": "transport", "skill_tags": ["route planning", "logistics", "customer service"], "experience_level": "mid", "salary_range": "Rs 34,000 – Rs 49,000"},
        {"title": "Ground Operations Assistant", "org_name": "Nepal Airlines Ground", "org_type": "private", "district": "Kathmandu", "trade_category": "transport", "skill_tags": ["cargo handling", "customer service", "logistics"], "experience_level": "entry", "salary_range": "Rs 31,000 – Rs 44,000"},
        {"title": "Logistics Coordinator", "org_name": "Himalayan Logistics", "org_type": "private", "district": "Biratnagar", "trade_category": "transport", "skill_tags": ["logistics", "route planning", "fleet management"], "experience_level": "mid", "salary_range": "Rs 37,000 – Rs 56,000"},
        {"title": "Greenhouse Technician", "org_name": "Agro Enterprise Centre", "org_type": "private", "district": "Chitwan", "trade_category": "agriculture", "skill_tags": ["greenhouse", "crop management", "pest control"], "experience_level": "entry", "salary_range": "Rs 25,000 – Rs 36,000"},
        {"title": "Supply Chain Supervisor", "org_name": "Fresh Produce Nepal", "org_type": "private", "district": "Butwal", "trade_category": "agriculture", "skill_tags": ["harvesting", "market selling", "inventory management"], "experience_level": "mid", "salary_range": "Rs 32,000 – Rs 47,000"},
        {"title": "Herbs Processing Officer", "org_name": "Himalayan Herbs", "org_type": "private", "district": "Pokhara", "trade_category": "manufacturing", "skill_tags": ["quality control", "packaging", "production planning"], "experience_level": "mid", "salary_range": "Rs 35,000 – Rs 54,000"},
        {"title": "Software Support Associate", "org_name": "Leapfrog Technology", "org_type": "private", "district": "Kathmandu", "trade_category": "tech", "skill_tags": ["IT support", "customer support", "web development"], "experience_level": "entry", "salary_range": "Rs 45,000 – Rs 70,000"},
        {"title": "Data Operations Specialist", "org_name": "Cotiviti Nepal", "org_type": "private", "district": "Kathmandu", "trade_category": "tech", "skill_tags": ["data entry", "customer support", "IT support"], "experience_level": "mid", "salary_range": "Rs 42,000 – Rs 66,000"},
        {"title": "Digital Outreach Coordinator", "org_name": "CloudFactory", "org_type": "private", "district": "Kathmandu", "trade_category": "tech", "skill_tags": ["digital marketing", "customer support", "social media"], "experience_level": "mid", "salary_range": "Rs 40,000 – Rs 62,000"},
        {"title": "Messaging Platform Support", "org_name": "Sparrow SMS", "org_type": "private", "district": "Lalitpur", "trade_category": "tech", "skill_tags": ["IT support", "networking", "customer support"], "experience_level": "mid", "salary_range": "Rs 38,000 – Rs 58,000"},
        {"title": "Machine Line Operator", "org_name": "Golcha Group", "org_type": "private", "district": "Biratnagar", "trade_category": "manufacturing", "skill_tags": ["machine operation", "assembly line", "quality control"], "experience_level": "entry", "salary_range": "Rs 27,000 – Rs 39,000"},
        {"title": "Factory Production Planner", "org_name": "CG Corp factories", "org_type": "private", "district": "Chitwan", "trade_category": "manufacturing", "skill_tags": ["production planning", "inventory management", "packaging"], "experience_level": "mid", "salary_range": "Rs 36,000 – Rs 55,000"},
        {"title": "Fabrication Supervisor", "org_name": "Reliance Spinning Mills", "org_type": "private", "district": "Butwal", "trade_category": "manufacturing", "skill_tags": ["fabrication", "welding", "quality control"], "experience_level": "senior", "salary_range": "Rs 48,000 – Rs 72,000"},
        {"title": "Childcare & Home Support Worker", "org_name": "Care Homes Nepal", "org_type": "private", "district": "Kathmandu", "trade_category": "domestic", "skill_tags": ["childcare", "cooking", "home management"], "experience_level": "entry", "salary_range": "Rs 24,000 – Rs 34,000"},
        {"title": "Community Livelihoods Officer", "org_name": "UN Women Nepal", "org_type": "ngo", "district": "Kathmandu", "trade_category": "hospitality", "skill_tags": ["event management", "guest relations", "customer service"], "experience_level": "mid", "salary_range": "Rs 55,000 – Rs 78,000"},
        {"title": "Digital Skills Trainer", "org_name": "UNDP Nepal", "org_type": "ngo", "district": "Lalitpur", "trade_category": "tech", "skill_tags": ["web development", "IT support", "digital marketing"], "experience_level": "mid", "salary_range": "Rs 58,000 – Rs 82,000"},
        {"title": "Youth Employability Coordinator", "org_name": "Plan International Nepal", "org_type": "ngo", "district": "Pokhara", "trade_category": "hospitality", "skill_tags": ["event management", "tour guiding", "guest relations"], "experience_level": "mid", "salary_range": "Rs 50,000 – Rs 72,000"},
        {"title": "Field Operations Officer", "org_name": "World Vision Nepal", "org_type": "ngo", "district": "Chitwan", "trade_category": "agriculture", "skill_tags": ["crop management", "market selling", "irrigation"], "experience_level": "mid", "salary_range": "Rs 46,000 – Rs 69,000"},
        {"title": "Recovery Livelihoods Assistant", "org_name": "Mercy Corps Nepal", "org_type": "ngo", "district": "Butwal", "trade_category": "manufacturing", "skill_tags": ["production planning", "inventory management", "packaging"], "experience_level": "entry", "salary_range": "Rs 38,000 – Rs 55,000"},
        {"title": "Program Associate - Skills", "org_name": "Save the Children Nepal", "org_type": "ngo", "district": "Kathmandu", "trade_category": "domestic", "skill_tags": ["childcare", "tutoring", "home management"], "experience_level": "mid", "salary_range": "Rs 44,000 – Rs 64,000"},
        {"title": "Community Enterprise Facilitator", "org_name": "Care Nepal", "org_type": "ngo", "district": "Bhaktapur", "trade_category": "agriculture", "skill_tags": ["organic farming", "market selling", "crop management"], "experience_level": "mid", "salary_range": "Rs 43,000 – Rs 63,000"},
        {"title": "Livestock Business Mentor", "org_name": "Heifer International Nepal", "org_type": "ngo", "district": "Chitwan", "trade_category": "agriculture", "skill_tags": ["livestock", "market selling", "crop management"], "experience_level": "senior", "salary_range": "Rs 52,000 – Rs 76,000"},
        {"title": "Transport Safety Trainer", "org_name": "ActionAid Nepal", "org_type": "ngo", "district": "Biratnagar", "trade_category": "transport", "skill_tags": ["heavy vehicle driving", "vehicle maintenance", "customer service"], "experience_level": "senior", "salary_range": "Rs 47,000 – Rs 68,000"},
        {"title": "Practical Skills Officer", "org_name": "Practical Action", "org_type": "ngo", "district": "Pokhara", "trade_category": "construction", "skill_tags": ["masonry", "plumbing", "safety management"], "experience_level": "mid", "salary_range": "Rs 48,000 – Rs 71,000"},
    ]

    return [_with_local_description(job) for job in base_jobs]


def _with_local_description(job: dict) -> dict:
    title = job["title"]
    trade = job["trade_category"]
    district = job["district"]
    skills = ", ".join(job["skill_tags"][:3])
    org = job["org_name"]

    trade_lines = {
        "construction": f"This role supports active infrastructure and building work in {district}, with day-to-day responsibility around {skills}.",
        "hospitality": f"This role supports hotels, tourism, and service operations in {district}, with strong emphasis on {skills}.",
        "manufacturing": f"This role supports factory and production operations in {district}, especially around {skills}.",
        "agriculture": f"This role supports local agribusiness and field operations in {district}, with practical use of {skills}.",
        "transport": f"This role supports transport and logistics service delivery in {district}, with focus on {skills}.",
        "tech": f"This role supports Nepal-based digital operations in {district}, with core work around {skills}.",
        "domestic": f"This role supports households and care services in {district}, with trusted responsibility for {skills}.",
    }

    community_line = (
        "Nepali returnees with GCC, Malaysia, or India work experience are encouraged to apply, "
        "especially if they can adapt their overseas discipline to local team culture."
    )
    readiness_line = (
        f"{org} is looking for someone who can start with realistic expectations about local salaries, "
        "communicate clearly in Nepali, and work within Nepal-based reporting structures."
    )

    payload = dict(job)
    payload["description"] = f"{trade_lines.get(trade, f'This role is based in {district}.')} {community_line} {readiness_line}"
    return payload
