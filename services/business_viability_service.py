from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from models import Profile


@dataclass(frozen=True)
class BusinessTemplate:
    title: str
    fit_reason: str
    base_startup_cost_npr: int
    base_working_capital_npr: int
    monthly_revenue_npr: int
    monthly_cost_npr: int
    risk_level: str
    first_steps: list[str]


BUSINESS_TEMPLATES: dict[str, list[BusinessTemplate]] = {
    "construction": [
        BusinessTemplate(
            title="Interior Finishing & Repair Service",
            fit_reason="Good for workers with hands-on site experience, basic tools, and contractor networks.",
            base_startup_cost_npr=420000,
            base_working_capital_npr=160000,
            monthly_revenue_npr=210000,
            monthly_cost_npr=132000,
            risk_level="moderate",
            first_steps=["Register as a local contractor", "Buy essential electrical and plumbing tools", "Line up two supplier contacts"],
        ),
        BusinessTemplate(
            title="Tile, Paint & Small Renovation Crew",
            fit_reason="Works well for returnees who handled finishing work and can start with a lean two-person crew.",
            base_startup_cost_npr=300000,
            base_working_capital_npr=120000,
            monthly_revenue_npr=165000,
            monthly_cost_npr=102000,
            risk_level="low",
            first_steps=["Build a photo portfolio of previous work", "Arrange a mason/painter partner", "Set a neighborhood-first pricing sheet"],
        ),
        BusinessTemplate(
            title="Light Equipment Rental & Site Support",
            fit_reason="Suited to workers who understand site operations and want a higher-ticket but scalable path.",
            base_startup_cost_npr=760000,
            base_working_capital_npr=220000,
            monthly_revenue_npr=280000,
            monthly_cost_npr=190000,
            risk_level="high",
            first_steps=["Prioritize one rentable machine category", "Check ward and municipality permissions", "Pre-negotiate maintenance support"],
        ),
    ],
    "hospitality": [
        BusinessTemplate(
            title="Tea, Snacks & Breakfast Counter",
            fit_reason="A strong fit for workers from hotel kitchens, food prep, and service roles.",
            base_startup_cost_npr=240000,
            base_working_capital_npr=100000,
            monthly_revenue_npr=145000,
            monthly_cost_npr=90000,
            risk_level="low",
            first_steps=["Choose a commuter-friendly location", "Finalize a tight starter menu", "Secure hygiene and food permits"],
        ),
        BusinessTemplate(
            title="Budget Lodge or Homestay Operations",
            fit_reason="Makes sense for returnees with front-desk and guest relations experience plus family property access.",
            base_startup_cost_npr=700000,
            base_working_capital_npr=260000,
            monthly_revenue_npr=255000,
            monthly_cost_npr=178000,
            risk_level="moderate",
            first_steps=["Check local tourism seasonality", "Set up booking channels", "Invest in room basics and staff training"],
        ),
        BusinessTemplate(
            title="Event Catering & Packed Meal Service",
            fit_reason="Best for workers with banquet, kitchen prep, and team-coordination experience.",
            base_startup_cost_npr=360000,
            base_working_capital_npr=145000,
            monthly_revenue_npr=190000,
            monthly_cost_npr=123000,
            risk_level="moderate",
            first_steps=["Test menu pricing with three sample packages", "Secure bulk ingredient suppliers", "Create a social media order channel"],
        ),
    ],
    "manufacturing": [
        BusinessTemplate(
            title="Packaging & Labeling Unit",
            fit_reason="A practical step for returnees with quality-control or production-line discipline.",
            base_startup_cost_npr=430000,
            base_working_capital_npr=170000,
            monthly_revenue_npr=225000,
            monthly_cost_npr=150000,
            risk_level="moderate",
            first_steps=["Choose one product niche", "Price packaging materials in bulk", "Find two anchor clients before launch"],
        ),
        BusinessTemplate(
            title="Metal Fabrication Workshop",
            fit_reason="Good for workers with welding and fabrication experience who can serve local builders and shops.",
            base_startup_cost_npr=650000,
            base_working_capital_npr=210000,
            monthly_revenue_npr=275000,
            monthly_cost_npr=188000,
            risk_level="high",
            first_steps=["Lease a safe workshop space", "Prioritize welding and cutting equipment", "Map nearby contractor demand"],
        ),
        BusinessTemplate(
            title="Small Garment Finishing Unit",
            fit_reason="Useful for returnees familiar with repetitive production systems and quality checks.",
            base_startup_cost_npr=320000,
            base_working_capital_npr=135000,
            monthly_revenue_npr=175000,
            monthly_cost_npr=112000,
            risk_level="low",
            first_steps=["Secure 1-2 subcontract orders", "Start with a minimal machine set", "Create a simple quality checklist"],
        ),
    ],
    "agriculture": [
        BusinessTemplate(
            title="Commercial Vegetable Tunnel Farm",
            fit_reason="Fits workers with irrigation, harvesting, or farm-supervision experience.",
            base_startup_cost_npr=510000,
            base_working_capital_npr=155000,
            monthly_revenue_npr=205000,
            monthly_cost_npr=128000,
            risk_level="moderate",
            first_steps=["Check irrigation reliability", "Choose two high-margin crops", "Secure one wholesale buyer before planting"],
        ),
        BusinessTemplate(
            title="Goat or Poultry Expansion Farm",
            fit_reason="Works for returnees comfortable with daily care routines and basic livestock management.",
            base_startup_cost_npr=460000,
            base_working_capital_npr=175000,
            monthly_revenue_npr=195000,
            monthly_cost_npr=131000,
            risk_level="moderate",
            first_steps=["Validate feed suppliers", "Plan disease-control with a local vet", "Phase stock purchases instead of buying all at once"],
        ),
        BusinessTemplate(
            title="Agro-input and Farm Support Shop",
            fit_reason="A viable option for returnees who know what local farmers actually need season by season.",
            base_startup_cost_npr=370000,
            base_working_capital_npr=150000,
            monthly_revenue_npr=172000,
            monthly_cost_npr=108000,
            risk_level="low",
            first_steps=["Choose a ward close to active farms", "Start with a lean inventory", "Add advisory support as a trust builder"],
        ),
    ],
    "domestic": [
        BusinessTemplate(
            title="Home Cleaning & Care Service",
            fit_reason="Strong fit for returnees from caregiving, housekeeping, and home-management roles.",
            base_startup_cost_npr=190000,
            base_working_capital_npr=85000,
            monthly_revenue_npr=120000,
            monthly_cost_npr=71000,
            risk_level="low",
            first_steps=["Package services clearly", "Prioritize trust and referrals", "Buy a simple branded cleaning kit"],
        ),
        BusinessTemplate(
            title="Childcare & After-school Support Center",
            fit_reason="Useful for workers with childcare and tutoring experience in urban areas.",
            base_startup_cost_npr=430000,
            base_working_capital_npr=125000,
            monthly_revenue_npr=175000,
            monthly_cost_npr=118000,
            risk_level="moderate",
            first_steps=["Check local permits", "Choose a safe, accessible room", "Start with a small weekday program"],
        ),
        BusinessTemplate(
            title="Meal Prep and Tiffin Service",
            fit_reason="A practical hybrid option for returnees with cooking and household organization skills.",
            base_startup_cost_npr=230000,
            base_working_capital_npr=95000,
            monthly_revenue_npr=138000,
            monthly_cost_npr=86000,
            risk_level="low",
            first_steps=["Design 2-3 rotating meal plans", "Pilot orders in one neighborhood", "Track delivery and food cost tightly"],
        ),
    ],
    "transport": [
        BusinessTemplate(
            title="Last-mile Delivery Service",
            fit_reason="Good for returnees with route planning and driver coordination experience.",
            base_startup_cost_npr=320000,
            base_working_capital_npr=130000,
            monthly_revenue_npr=175000,
            monthly_cost_npr=118000,
            risk_level="moderate",
            first_steps=["Start with one dense delivery zone", "Partner with 3-5 local businesses", "Use GPS-based route planning from day one"],
        ),
        BusinessTemplate(
            title="Transport Booking & Fleet Support Desk",
            fit_reason="Makes sense for workers who understand scheduling, vehicle uptime, and customer calls.",
            base_startup_cost_npr=240000,
            base_working_capital_npr=95000,
            monthly_revenue_npr=145000,
            monthly_cost_npr=90000,
            risk_level="low",
            first_steps=["Build a trusted driver list", "Offer a narrow service first", "Track daily utilization and cancellations"],
        ),
        BusinessTemplate(
            title="Cargo Handling & Relocation Service",
            fit_reason="Fits returnees with logistics exposure and local labor coordination ability.",
            base_startup_cost_npr=410000,
            base_working_capital_npr=155000,
            monthly_revenue_npr=205000,
            monthly_cost_npr=142000,
            risk_level="moderate",
            first_steps=["Start with small commercial clients", "Buy safety and lifting essentials", "Define service packages clearly"],
        ),
    ],
    "tech": [
        BusinessTemplate(
            title="Digital Service Studio",
            fit_reason="A lean path for returnees with IT support, design, or digital operations experience.",
            base_startup_cost_npr=210000,
            base_working_capital_npr=80000,
            monthly_revenue_npr=135000,
            monthly_cost_npr=76000,
            risk_level="low",
            first_steps=["Define one strong service niche", "Create a small portfolio", "Find first clients through existing contacts"],
        ),
        BusinessTemplate(
            title="Cyber, Print & Online Form Center",
            fit_reason="Useful in district hubs where digital support and form help are still in demand.",
            base_startup_cost_npr=290000,
            base_working_capital_npr=100000,
            monthly_revenue_npr=150000,
            monthly_cost_npr=98000,
            risk_level="low",
            first_steps=["Choose a location near government or education traffic", "Bundle print, scan, and online services", "Keep pricing transparent"],
        ),
        BusinessTemplate(
            title="SME Social Media & Ads Service",
            fit_reason="Strong fit for returnees with digital marketing or customer support skills.",
            base_startup_cost_npr=180000,
            base_working_capital_npr=70000,
            monthly_revenue_npr=130000,
            monthly_cost_npr=72000,
            risk_level="moderate",
            first_steps=["Build 3 sample packages", "Start with local merchants", "Show clear before-and-after performance snapshots"],
        ),
    ],
    "other": [
        BusinessTemplate(
            title="Neighborhood Retail & Service Kiosk",
            fit_reason="A flexible low-capex option when the user’s trade is still broad or mixed.",
            base_startup_cost_npr=260000,
            base_working_capital_npr=100000,
            monthly_revenue_npr=145000,
            monthly_cost_npr=95000,
            risk_level="low",
            first_steps=["Start with one narrow product mix", "Test foot traffic at two locations", "Keep inventory discipline from day one"],
        ),
        BusinessTemplate(
            title="Skill-based Contract Service",
            fit_reason="Useful when the returnee has transferable skills but needs a flexible starting point.",
            base_startup_cost_npr=220000,
            base_working_capital_npr=90000,
            monthly_revenue_npr=138000,
            monthly_cost_npr=85000,
            risk_level="moderate",
            first_steps=["Package services into simple offers", "Ask former employers and relatives for referrals", "Track job profitability weekly"],
        ),
        BusinessTemplate(
            title="Community-focused Micro Franchise",
            fit_reason="A more structured option for returnees who prefer an existing operating model.",
            base_startup_cost_npr=480000,
            base_working_capital_npr=140000,
            monthly_revenue_npr=205000,
            monthly_cost_npr=138000,
            risk_level="moderate",
            first_steps=["Compare 2-3 franchise or distribution models", "Check local demand carefully", "Negotiate for lean starting inventory"],
        ),
    ],
}

DISTRICT_MULTIPLIERS = {
    "Kathmandu": 1.22,
    "Lalitpur": 1.18,
    "Bhaktapur": 1.12,
    "Pokhara": 1.15,
    "Chitwan": 1.08,
    "Biratnagar": 1.05,
    "Butwal": 1.04,
}

SAVINGS_RANGE_DEFAULTS = {
    "under_5L": 350000,
    "5L_to_20L": 800000,
    "20L_to_50L": 2500000,
    "above_50L": 5500000,
}


def _enum_value(value: Any) -> str | None:
    return value.value if hasattr(value, "value") else value


def infer_savings_amount_npr(profile: Profile | None) -> int:
    if not profile:
        return 800000
    savings_range = _enum_value(getattr(profile, "savings_range", None))
    return SAVINGS_RANGE_DEFAULTS.get(str(savings_range), 800000)


def _district_multiplier(district: str | None) -> float:
    return DISTRICT_MULTIPLIERS.get(str(district or "Kathmandu"), 1.0)


def _round_to_nearest_thousand(value: float) -> int:
    return int(round(value / 1000.0) * 1000)


def _revenue_range_text(midpoint: int) -> str:
    low = _round_to_nearest_thousand(midpoint * 0.88)
    high = _round_to_nearest_thousand(midpoint * 1.15)
    return f"NPR {low:,} - {high:,}"


def build_viability_options(trade_category: str, district: str, savings_amount_npr: int) -> list[dict[str, Any]]:
    templates = BUSINESS_TEMPLATES.get(trade_category, BUSINESS_TEMPLATES["other"])
    multiplier = _district_multiplier(district)
    options: list[dict[str, Any]] = []

    for template in templates[:3]:
        startup = _round_to_nearest_thousand(template.base_startup_cost_npr * multiplier)
        working_capital = _round_to_nearest_thousand(template.base_working_capital_npr * (0.96 + (multiplier - 1) * 0.5))
        total_cost = startup + working_capital
        monthly_revenue = _round_to_nearest_thousand(template.monthly_revenue_npr * (0.95 + (multiplier - 1) * 0.35))
        monthly_cost = _round_to_nearest_thousand(template.monthly_cost_npr * (0.97 + (multiplier - 1) * 0.35))
        monthly_profit = max(monthly_revenue - monthly_cost, 20000)
        break_even = max(4, min(24, round(total_cost / monthly_profit)))
        savings_gap = max(0, total_cost - savings_amount_npr)

        risk_level = template.risk_level
        if savings_gap > 200000 and risk_level == "moderate":
            risk_level = "high"
        elif savings_gap == 0 and risk_level == "moderate" and break_even <= 8:
            risk_level = "low"

        options.append(
            {
                "title": template.title,
                "fit_reason": template.fit_reason,
                "startup_cost_npr": startup,
                "working_capital_npr": working_capital,
                "total_estimated_cost_npr": total_cost,
                "savings_gap_npr": savings_gap,
                "break_even_months": break_even,
                "risk_level": risk_level,
                "monthly_revenue_range_npr": _revenue_range_text(monthly_revenue),
                "monthly_cost_range_npr": _revenue_range_text(monthly_cost),
                "suggested_first_steps": template.first_steps,
            }
        )

    return options

