import re
from typing import Any
from urllib.parse import urlparse

from ddgs import DDGS

BLOCKED_DOMAINS = {
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "youtube.com",
    "twitter.com",
    "x.com",
    "microsoft.com",
    "google.com",
    "wikipedia.org",
    "reddit.com",
}


def _normalize_location(location: str) -> str:
    loc = (location or "Dubai").strip()
    if loc.lower() in {"uae", "emirates"}:
        return "Dubai UAE"
    return loc


def _dedupe_results(results: list[dict[str, str]]) -> list[dict[str, str]]:
    seen_urls: set[str] = set()
    unique: list[dict[str, str]] = []

    for item in results:
        url = (item.get("url") or "").strip()
        if not url or url in seen_urls:
            continue
        domain = urlparse(url).netloc.lower().replace("www.", "")
        if any(blocked in domain for blocked in BLOCKED_DOMAINS):
            continue
        seen_urls.add(url)
        unique.append(item)

    return unique


def _run_search(query: str, max_results: int = 6) -> list[dict[str, str]]:
    try:
        raw = DDGS().text(query, max_results=max_results)
        results = []
        for row in raw:
            url = (row.get("href") or row.get("url") or "").strip()
            title = (row.get("title") or "").strip()
            snippet = (row.get("body") or row.get("snippet") or "").strip()
            if url and title:
                results.append({"title": title, "url": url, "snippet": snippet})
        return results
    except Exception:
        return []


def search_exhibition_contractors(requirements: dict[str, Any]) -> list[dict[str, str]]:
    location = _normalize_location(requirements.get("location", "Dubai"))
    budget = int(requirements.get("budget") or 0)
    booth_size = requirements.get("booth_size") or "6x6"
    industry = requirements.get("industry") or "exhibition"

    if budget and budget < 25000:
        budget_terms = "affordable budget cheap economical"
    elif budget and budget < 60000:
        budget_terms = "affordable mid-range cost effective"
    else:
        budget_terms = "custom premium professional"

    queries = [
        f"{budget_terms} exhibition stand builder contractor {location} UAE",
        f"exhibition booth design build company {location} {booth_size}",
        f"{industry} exhibition stand contractor {location} UAE website",
        f"portable modular exhibition stand supplier {location} UAE price",
    ]

    if budget:
        queries.append(
            f"exhibition stand {location} budget {budget} AED"
        )

    combined: list[dict[str, str]] = []
    for query in queries:
        combined.extend(_run_search(query, max_results=5))

    return _dedupe_results(combined)[:12]
