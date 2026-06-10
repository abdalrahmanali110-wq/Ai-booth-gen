from typing import Any

CURATED_UAE_SUPPLIERS = [
    {
        "name": "Dome Exhibitions",
        "url": "http://www.domeexhibitions.ae/",
        "tier": "value",
        "estimated_cost": 35000,
        "location": "Dubai",
        "category": "Exhibition stand contractor",
    },
    {
        "name": "Alsaif Graphic",
        "url": "https://alsaifgr.ae/",
        "tier": "value",
        "estimated_cost": 28000,
        "location": "Dubai",
        "category": "Exhibition stand & event production",
    },
    {
        "name": "Elegant Qubes Dubai",
        "url": "https://www.elegantqubes.com/",
        "tier": "value",
        "estimated_cost": 45000,
        "location": "Dubai",
        "category": "Exhibition stand contractors",
    },
    {
        "name": "Screen Craft",
        "url": "https://www.screencraft.ae/",
        "tier": "value",
        "estimated_cost": 40000,
        "location": "Dubai",
        "category": "Exhibition stand builders",
    },
    {
        "name": "Regal Exhibitions & Events",
        "url": "https://regalexhibitions.com/",
        "tier": "value",
        "estimated_cost": 38000,
        "location": "Dubai",
        "category": "Exhibition & events",
    },
    {
        "name": "Maple Exhibition Organizing",
        "url": "https://www.mapleexpo.com/",
        "tier": "premium",
        "estimated_cost": 90000,
        "location": "Dubai",
        "category": "Premium corporate exhibitions",
    },
    {
        "name": "Level Exhibition",
        "url": "https://www.levelexhibition.com/",
        "tier": "premium",
        "estimated_cost": 85000,
        "location": "Dubai",
        "category": "Premium stand design & build",
    },
    {
        "name": "STROKES EXHIBITS",
        "url": "https://www.strokesexhibits.com/",
        "tier": "premium",
        "estimated_cost": 88000,
        "location": "Dubai",
        "category": "Custom exhibition stands",
    },
]


def get_curated_suppliers_for_budget(
    requirements: dict[str, Any],
    budget_analysis: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    user_budget = int(budget_analysis.get("user_budget") or 0)
    fits = budget_analysis.get("fits_budget", False)

    budget_pool = [
        s for s in CURATED_UAE_SUPPLIERS if s["tier"] == "value"
    ]
    premium_pool = [
        s for s in CURATED_UAE_SUPPLIERS if s["tier"] == "premium"
    ]

    if user_budget > 0:
        budget_pool = sorted(
            budget_pool,
            key=lambda s: abs(s["estimated_cost"] - user_budget),
        )
        premium_pool = sorted(
            premium_pool,
            key=lambda s: s["estimated_cost"],
        )

    budget_companies = [
        {
            "name": s["name"],
            "url": s["url"],
            "snippet": s["category"],
            "why_recommended": (
                f"Curated UAE contractor — typical projects from "
                f"AED {max(user_budget, s['estimated_cost'] - 10000):,} "
                f"for modular/custom stands."
            ),
            "estimated_range": f"AED {s['estimated_cost'] - 8000:,} – {s['estimated_cost'] + 12000:,}",
            "tier": "budget-friendly",
        }
        for s in budget_pool[:4]
    ]

    stretch_companies = []
    if user_budget > 0 and not fits:
        stretch_companies = [
            {
                "name": s["name"],
                "url": s["url"],
                "snippet": s["category"],
                "why_recommended": "Premium option if you increase budget.",
                "estimated_range": f"AED {s['estimated_cost']:,}+",
                "tier": "premium",
            }
            for s in premium_pool[:2]
        ]

    return {
        "budget_companies": budget_companies,
        "stretch_companies": stretch_companies,
    }


def recommend_suppliers(industry: str) -> list[dict]:
    return [
        {
            "name": s["name"],
            "category": s["category"],
            "estimated_cost": s["estimated_cost"],
            "website": s["url"],
            "location": s["location"],
        }
        for s in CURATED_UAE_SUPPLIERS
        if s["tier"] == "value"
    ][:3]
