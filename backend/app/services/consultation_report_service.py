import re
from typing import Any

from app.services.gemma_service import (
    curate_supplier_recommendations,
    generate_booth_feature_analysis,
)
from app.services.supplier_service import get_curated_suppliers_for_budget
from app.services.web_search_service import search_exhibition_contractors

# Realistic UAE market rates (AED per sqm, build only — excludes organiser fees)
MARKET_RATES = {
    "economy": (350, 650),
    "standard": (750, 1400),
    "premium": (1500, 2500),
    "luxury": (2500, 4500),
}

COST_TABLE = [
    {
        "size": "36 sqm (6x6)",
        "standard": "AED 27,000 – 50,000",
        "premium": "AED 54,000 – 90,000",
        "luxury": "AED 90,000+",
    },
    {
        "size": "49 sqm (7x7)",
        "standard": "AED 37,000 – 69,000",
        "premium": "AED 74,000 – 123,000",
        "luxury": "AED 123,000+",
    },
    {
        "size": "64 sqm (8x8)",
        "standard": "AED 48,000 – 90,000",
        "premium": "AED 96,000 – 160,000",
        "luxury": "AED 160,000+",
    },
]


def _parse_booth_size(booth_size: str) -> tuple[int, int, int]:
    match = re.search(r"(\d+)\s*[x×]\s*(\d+)", (booth_size or "").lower())
    if not match:
        return 6, 6, 36
    width, depth = int(match.group(1)), int(match.group(2))
    return width, depth, width * depth


def _normalize_special(requirements: dict[str, Any]) -> list[str]:
    special = requirements.get("special_requirements") or []
    if isinstance(special, str):
        return [part.strip() for part in re.split(r"[,;]", special) if part.strip()]
    return [str(item).strip() for item in special if str(item).strip()]


def _complexity_score(requirements: dict[str, Any]) -> float:
    special = _normalize_special(requirements)
    score = 1.0 + len(special) * 0.08
    theme = (requirements.get("theme") or "").lower()
    if any(word in theme for word in ("luxury", "premium", "metallic", "high-end")):
        score += 0.2
    return min(score, 1.6)


def _tier_from_budget_per_sqm(budget_per_sqm: float) -> str:
    if budget_per_sqm >= 2500:
        return "luxury"
    if budget_per_sqm >= 1500:
        return "premium"
    if budget_per_sqm >= 750:
        return "standard"
    return "economy"


def _vision_tier(requirements: dict[str, Any]) -> str:
    special_count = len(_normalize_special(requirements))
    theme = (requirements.get("theme") or "").lower()
    if special_count >= 4 or any(
        word in theme for word in ("luxury", "premium", "metallic", "high-end", "rock")
    ):
        return "premium"
    if special_count >= 2:
        return "standard"
    return "standard"


def analyze_budget(requirements: dict[str, Any]) -> dict[str, Any]:
    user_budget = int(requirements.get("budget") or 0)
    width, depth, sqm = _parse_booth_size(requirements.get("booth_size", "6x6"))
    complexity = _complexity_score(requirements)

    achievable_tier = "standard"
    market_low = int(MARKET_RATES["standard"][0] * sqm * complexity)
    market_high = int(MARKET_RATES["premium"][1] * sqm * complexity)
    vision = _vision_tier(requirements)

    if user_budget > 0:
        budget_per_sqm = user_budget / sqm
        achievable_tier = _tier_from_budget_per_sqm(budget_per_sqm)
        low_rate, high_rate = MARKET_RATES[achievable_tier]
        market_low = int(low_rate * sqm * complexity)
        market_high = int(high_rate * sqm * complexity)

    vision_low = int(MARKET_RATES[vision][0] * sqm * complexity)
    vision_high = int(MARKET_RATES[vision][1] * sqm * complexity)

    fits_budget = user_budget >= vision_low if user_budget else False
    gap = max(0, vision_low - user_budget) if user_budget else 0

    if user_budget <= 0:
        summary = (
            f"For a {width}m x {depth}m ({sqm} sqm) booth in the UAE, "
            f"expect roughly AED {vision_low:,}–{vision_high:,} for a "
            f"{vision} build (excluding organiser fees)."
        )
    elif fits_budget:
        summary = (
            f"Your budget of AED {user_budget:,} can support a "
            f"{achievable_tier} build for {sqm} sqm. "
            f"Typical range: AED {market_low:,}–{market_high:,}."
        )
    else:
        summary = (
            f"Your budget of AED {user_budget:,} is below the typical minimum "
            f"of AED {vision_low:,} for a {vision} custom booth at {sqm} sqm "
            f"(about AED {gap:,} short). Consider modular/portable builds, "
            f"rental stands, or reducing custom features."
        )

    return {
        "user_budget": user_budget,
        "booth_size": requirements.get("booth_size") or f"{width}x{depth}",
        "sqm": sqm,
        "achievable_tier": achievable_tier,
        "vision_tier": vision,
        "market_range_low": market_low,
        "market_range_high": market_high,
        "vision_range_low": vision_low,
        "vision_range_high": vision_high,
        "fits_budget": fits_budget,
        "budget_gap_aed": gap,
        "summary": summary,
    }


def _rule_based_features(requirements: dict[str, Any], budget_analysis: dict) -> list[str]:
    theme = requirements.get("theme") or "brand"
    special = _normalize_special(requirements)
    tier = budget_analysis["achievable_tier"]
    combined = " ".join(special).lower()

    if tier == "economy":
        features = [
            "Modular or portable stand system with branded graphics",
            "Basic reception counter or plinth",
            "Standard spot lighting",
            "Printed branding panels",
        ]
    elif tier == "standard":
        features = [
            f"Custom MDF/wood finishes in {theme} styling",
            "Integrated LED strip lighting",
            "Branded reception counter",
            "Product display shelving",
            "Storage cupboard",
        ]
    else:
        features = [
            f"High-quality wood/MDF finishes in {theme} styling",
            "Integrated LED lighting and illuminated fascia",
            "Custom shelving and display walls",
            "Reception counter",
            "Large digital screens",
            "Storage area",
            "Premium flooring",
        ]

    if any("guitar" in item for item in special):
        features.append("Wall-mounted product/guitar displays")
    if any("record" in item for item in special):
        features.append("Dedicated media/record display shelving")
    if any(word in combined for word in ("play", "performance", "stage")):
        features.append("Small demo or performance zone")
    if any(word in combined for word in ("cash", "casher", "counter", "pos")):
        features.append("Cashier / POS counter")
    if any(word in combined for word in ("led", "light")):
        features.append("Accent LED feature lighting")

    if not budget_analysis["fits_budget"] and tier == "economy":
        features.append(
            "Note: premium features from the concept may need to be simplified "
            "or phased to stay within budget"
        )

    seen: set[str] = set()
    unique: list[str] = []
    for feature in features:
        key = feature.lower()
        if key not in seen:
            seen.add(key)
            unique.append(feature)
    return unique


def _size_note(requirements: dict[str, Any]) -> str:
    width, depth, sqm = _parse_booth_size(requirements.get("booth_size", "6x6"))
    return (
        f"Requested booth size: {width}m x {depth}m ({sqm} sqm). "
        f"Final footprint depends on venue allocation and aisle rules."
    )


def _budget_recommendation(
    requirements: dict[str, Any],
    budget_analysis: dict[str, Any],
) -> str:
    user_budget = budget_analysis["user_budget"]
    if user_budget > 0 and budget_analysis["fits_budget"]:
        return (
            f"Working within your AED {user_budget:,} budget, target contractors "
            f"quoting AED {budget_analysis['market_range_low']:,}–"
            f"{budget_analysis['market_range_high']:,} for the build itself. "
            f"Add 15–25% buffer for graphics, logistics, and on-site costs."
        )

    if user_budget > 0:
        return (
            f"To match the generated concept more closely, consider increasing "
            f"budget toward AED {budget_analysis['vision_range_low']:,}–"
            f"{budget_analysis['vision_range_high']:,}. "
            f"With AED {user_budget:,}, focus on modular builds, rental elements, "
            f"or fewer custom fabrications."
        )

    return (
        f"For this size and feature set in the UAE, plan around "
        f"AED {budget_analysis['vision_range_low']:,}–"
        f"{budget_analysis['vision_range_high']:,} excluding organiser fees."
    )


def _suppliers_from_saved(saved_suppliers: list[dict] | None) -> list[dict[str, Any]]:
    if not saved_suppliers:
        return []

    companies = []
    for row in saved_suppliers:
        companies.append(
            {
                "name": row.get("company_name") or "Unknown",
                "url": row.get("website_url") or "",
                "snippet": row.get("description") or "",
                "why_recommended": row.get("description") or "",
                "estimated_range": "",
                "tier": "budget-friendly"
                if "value" in (row.get("source") or "")
                else "recommended",
            }
        )
    return companies


def _format_markdown(report: dict[str, Any]) -> str:
    lines = [report["intro"], ""]
    for feature in report["features"]:
        lines.append(f"- {feature}")

    lines.extend(["", report["size_note"], "", report["budget_analysis"]["summary"], ""])
    lines.append("Estimated Cost in Dubai/UAE")
    lines.append(
        "Booth Size | Standard | Premium | Luxury"
    )
    for row in report["cost_table"]:
        lines.append(
            f"{row['size']} | {row['standard']} | {row['premium']} | {row['luxury']}"
        )

    lines.extend(["", report["budget_recommendation"], ""])
    lines.append(f"Recommended Companies ({report['location']}) — web search results")

    for company in report.get("web_companies") or []:
        url = company.get("url") or ""
        line = company["name"]
        if url:
            line += f" — {url}"
        lines.append(line)
        if company.get("why_recommended"):
            lines.append(f"  {company['why_recommended']}")

    if report.get("stretch_companies"):
        lines.extend(["", "If you can increase budget:"])
        for company in report["stretch_companies"]:
            url = company.get("url") or ""
            line = company["name"]
            if url:
                line += f" — {url}"
            lines.append(line)

    return "\n".join(lines)


def _search_results_to_companies(
    search_results: list[dict[str, str]],
    budget_analysis: dict[str, Any],
) -> list[dict[str, Any]]:
    user_budget = budget_analysis.get("user_budget") or 0
    companies = []

    for index, result in enumerate(search_results[:5]):
        title = result.get("title") or f"Contractor {index + 1}"
        name = re.sub(r"\s*[\-|–|—].*$", "", title).strip()[:80]
        companies.append(
            {
                "name": name,
                "url": result.get("url") or "",
                "snippet": result.get("snippet") or "",
                "why_recommended": (
                    result.get("snippet") or "UAE exhibition stand contractor from web search."
                )[:200],
                "estimated_range": (
                    f"Request quote — target under AED {user_budget:,}"
                    if user_budget
                    else "Request quote for your booth size"
                ),
                "tier": "budget-friendly",
            }
        )

    return companies


def generate_consultation_report(
    requirements: dict[str, Any],
    *,
    saved_suppliers: list[dict] | None = None,
    skip_web_search: bool = False,
) -> dict[str, Any]:
    budget_analysis = analyze_budget(requirements)
    llm_features = generate_booth_feature_analysis(requirements, budget_analysis)
    features = llm_features or _rule_based_features(requirements, budget_analysis)

    web_companies: list[dict[str, Any]] = []
    stretch_companies: list[dict[str, Any]] = []
    cost_saving_tips: list[str] = []

    if skip_web_search and saved_suppliers:
        web_companies = _suppliers_from_saved(saved_suppliers)
    else:
        search_results = search_exhibition_contractors(requirements)
        curated = curate_supplier_recommendations(
            requirements,
            budget_analysis,
            search_results,
        )
        if curated:
            web_companies = curated.get("budget_companies") or []
            stretch_companies = curated.get("stretch_companies") or []
            cost_saving_tips = curated.get("cost_saving_tips") or []

        if not web_companies and search_results:
            web_companies = _search_results_to_companies(
                search_results,
                budget_analysis,
            )

        if not web_companies:
            fallback = get_curated_suppliers_for_budget(requirements, budget_analysis)
            web_companies = fallback.get("budget_companies") or []
            stretch_companies = fallback.get("stretch_companies") or []

    achievable_tier = budget_analysis["achievable_tier"]
    intro = (
        f"Based on your AED {budget_analysis['user_budget']:,} budget, "
        f"this concept targets a {achievable_tier} custom exhibition booth with:"
        if budget_analysis["user_budget"]
        else "Based on your brief, this exhibition booth concept includes:"
    )

    report = {
        "intro": intro,
        "features": features,
        "size_note": _size_note(requirements),
        "budget_analysis": budget_analysis,
        "cost_table": COST_TABLE,
        "budget_recommendation": _budget_recommendation(requirements, budget_analysis),
        "quality_tier": achievable_tier,
        "web_companies": web_companies,
        "stretch_companies": stretch_companies,
        "cost_saving_tips": cost_saving_tips,
        "location": requirements.get("location") or "Dubai",
        # Legacy keys for older UI paths
        "premium_companies": stretch_companies,
        "value_companies": web_companies,
    }
    report["markdown"] = _format_markdown(report)
    return report
