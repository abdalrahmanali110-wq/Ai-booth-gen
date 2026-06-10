import json
import re

import httpx

from app.core.config import GEMMA_MODEL, OPENROUTER_API_KEY, SITE_URL

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

REQUIREMENT_FIELDS = [
    "industry",
    "event_name",
    "booth_size",
    "budget",
    "theme",
    "location",
    "special_requirements",
]

CHAT_SYSTEM_PROMPT = """You are an AI Exhibition Booth Consultant for a client-facing production app.

Collect booth requirements through natural conversation, one question at a time.

Fields to collect (any order):
- industry, event_name, booth_size, budget (AED), theme, location, special_requirements

Rules:
- Ask only ONE question per reply, for the next missing field shown in the context.
- Accept information in any order.
- Be professional, concise, and friendly.
- You CANNOT generate images. Never say you are generating or creating images.
- When all fields are collected, say:
  "Great, I have everything I need. Starting booth generation now."
- Do not invent requirements the user did not provide.
"""


def _openrouter_headers() -> dict:
    return {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": SITE_URL,
        "X-Title": "AI Booth Generator",
    }


def _parse_json_response(content: str) -> dict:
    if not content:
        return {}

    content = content.strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{[\s\S]*\}", content)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            return {}

    return {}


def _parse_budget_amount(text: str) -> int | None:
    normalized = text.lower().replace(",", "").strip()
    match = re.search(r"(\d+(?:\.\d+)?)\s*k\b", normalized)
    if match:
        return int(float(match.group(1)) * 1000)

    for match in re.finditer(r"\d+", normalized.replace(" ", "")):
        value = int(match.group())
        if value >= 500:
            return value

    return None


def _parse_booth_size(text: str) -> str | None:
    match = re.search(r"(\d+)\s*[x×]\s*(\d+)", text, re.I)
    if match:
        return f"{match.group(1)}x{match.group(2)}"
    return None


def _last_assistant_message(messages: list[dict]) -> str:
    for message in reversed(messages):
        if message.get("role") == "assistant" and message.get("content"):
            return message["content"]
    return ""


def _sanitize_requirements(requirements: dict) -> dict:
    budget = requirements.get("budget")
    booth_size = requirements.get("booth_size") or ""

    if budget is not None and booth_size:
        size_digits = re.sub(r"[^0-9]", "", booth_size)
        if size_digits and budget == int(size_digits):
            requirements["budget"] = None
        if budget < 500 and "x" in booth_size.lower():
            requirements["budget"] = None

    return requirements


def _missing_fields(requirements: dict) -> list[str]:
    order = [
        "industry",
        "event_name",
        "booth_size",
        "budget",
        "theme",
        "location",
    ]
    missing = [field for field in order if not requirements.get(field)]
    if requirements.get("special_requirements") is None:
        missing.append("special_requirements")
    return missing


def _looks_like_event(text: str) -> bool:
    return bool(
        re.search(
            r"\b(expo|exhibition|fair|conference|summit|forum|show)\b",
            text,
            re.I,
        )
    )


def _infer_target_field(
    text: str,
    question: str,
    missing: list[str],
) -> str | None:
    q = question.lower()

    if _parse_booth_size(text) and "booth_size" in missing:
        return "booth_size"
    if _parse_budget_amount(text) and "budget" in missing:
        return "budget"
    if _looks_like_event(text) and "event_name" in missing:
        return "event_name"
    if "theme" in missing and re.search(
        r"\b(cozy|modern|luxury|wooden|rustic|elegant|colorful|warm|minimalist|"
        r"vintage|futuristic|classic|bright|dark)\b",
        text,
        re.I,
    ):
        return "theme"
    if "theme" in missing and len(text.split()) >= 4:
        return "theme"
    if "special_requirements" in missing and "," in text:
        return "special_requirements"
    if (
        "location" in missing
        and len(text.split()) == 1
        and re.fullmatch(r"[A-Za-z][A-Za-z\-]+", text)
        and not _looks_like_event(text)
        and not _parse_budget_amount(text)
    ):
        return "location"

    field_by_question = [
        (r"industry|business|sector|field", "industry"),
        (r"event|exhibition|expo|fair|conference", "event_name"),
        (r"booth size|what size|dimensions", "booth_size"),
        (r"budget|aed|spend|price|cost", "budget"),
        (r"theme|style|aesthetic|look and feel", "theme"),
        (r"city|location|where.*event|take place", "location"),
        (r"special|requirement|feature", "special_requirements"),
    ]
    for pattern, field in field_by_question:
        if re.search(pattern, q) and field in missing:
            return field
    if (
        "theme" in missing
        and len(text.split()) >= 2
        and not _parse_budget_amount(text)
        and not _parse_booth_size(text)
    ):
        return "theme"

    return missing[0] if missing else None


def contextual_extract_from_turn(
    messages: list[dict],
    user_message: str,
    current: dict,
) -> dict:
    """Infer which requirement field a user answer belongs to."""
    updated = {**current}
    text = user_message.strip()
    if not text:
        return updated

    question = _last_assistant_message(messages)
    missing = _missing_fields(updated)
    lower = text.lower()
    field = _infer_target_field(text, question, missing)

    if not field:
        return _sanitize_requirements(updated)

    if field == "booth_size":
        size = _parse_booth_size(text)
        if size:
            updated["booth_size"] = size
    elif field == "budget":
        amount = _parse_budget_amount(text)
        if amount:
            updated["budget"] = amount
    elif field == "special_requirements":
        if lower in {"none", "no", "n/a", "nothing", "skip"}:
            updated["special_requirements"] = []
        else:
            updated["special_requirements"] = [
                part.strip()
                for part in re.split(r"[,;]", text)
                if part.strip()
            ]
    else:
        updated[field] = text

    return _sanitize_requirements(updated)


def chat_reply(
    history: list[dict],
    user_message: str,
    requirements: dict,
    *,
    next_question: str | None = None,
) -> dict | None:
    """Generate a conversational reply. Requirements are extracted separately."""
    if not OPENROUTER_API_KEY:
        return None

    context = (
        f"Current collected requirements:\n"
        f"{json.dumps(requirements, indent=2)}\n\n"
    )
    if next_question:
        context += (
            f"Ask this next question (you may rephrase naturally): {next_question}"
        )
    else:
        context += "All requirements are collected."

    messages = [
        {"role": "system", "content": CHAT_SYSTEM_PROMPT},
        *history,
        {"role": "user", "content": user_message},
        {"role": "system", "content": context},
    ]

    payload = {
        "model": GEMMA_MODEL,
        "messages": messages,
        "temperature": 0.5,
    }

    try:
        response = httpx.post(
            OPENROUTER_API_URL,
            headers=_openrouter_headers(),
            json=payload,
            timeout=90.0,
        )

        if response.status_code != 200:
            return None

        message = response.json()["choices"][0]["message"]
        content = (message.get("content") or "").strip()

        if not content:
            return None

        return {
            "reply": content,
            "reasoning_details": message.get("reasoning_details"),
        }
    except Exception:
        return None


def generate_booth_feature_analysis(
    requirements: dict,
    budget_analysis: dict | None = None,
) -> list[str] | None:
    """Use the LLM to describe booth build features from collected requirements."""
    if not OPENROUTER_API_KEY:
        return None

    budget_context = ""
    if budget_analysis:
        budget_context = (
            f"\nBudget analysis:\n{json.dumps(budget_analysis, indent=2)}\n"
            "Only list features realistically achievable within the user's budget tier. "
            "If budget is tight, include simplified alternatives."
        )

    prompt = (
        "Analyze this exhibition booth project for the UAE market. "
        "Return ONLY valid JSON with this shape:\n"
        '{"features": ["feature 1", "feature 2", "..."]}\n\n'
        "List 5-8 specific physical build features (materials, lighting, "
        "displays, counters, flooring, etc.) that match the requirements AND budget. "
        "Do not include pricing or company names.\n\n"
        f"Requirements:\n{json.dumps(requirements, indent=2)}"
        f"{budget_context}"
    )

    payload = {
        "model": GEMMA_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an exhibition booth analyst. "
                    "Respond with JSON only."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.4,
    }

    try:
        response = httpx.post(
            OPENROUTER_API_URL,
            headers=_openrouter_headers(),
            json=payload,
            timeout=60.0,
        )
        if response.status_code != 200:
            return None

        content = (response.json()["choices"][0]["message"].get("content") or "").strip()
        parsed = _parse_json_response(content)
        features = parsed.get("features")
        if isinstance(features, list) and len(features) >= 4:
            return [str(item).strip() for item in features if str(item).strip()]
    except Exception:
        return None

    return None


def curate_supplier_recommendations(
    requirements: dict,
    budget_analysis: dict,
    search_results: list[dict],
) -> dict | None:
    """Use LLM to pick real web search results that fit the user's budget."""
    if not OPENROUTER_API_KEY or not search_results:
        return None

    prompt = (
        "You are a UAE exhibition procurement advisor. "
        "Pick real companies from the web search results below that best match "
        "the client's budget. Prefer affordable options when budget is limited. "
        "Return ONLY valid JSON:\n"
        "{\n"
        '  "budget_companies": [\n'
        "    {\n"
        '      "name": "Company name",\n'
        '      "url": "https://...",\n'
        '      "why_recommended": "1 sentence why it fits the budget",\n'
        '      "estimated_range": "AED X – Y",\n'
        '      "tier": "budget-friendly"\n'
        "    }\n"
        "  ],\n"
        '  "stretch_companies": [ same shape, only if budget is below vision tier ],\n'
        '  "cost_saving_tips": ["tip 1", "tip 2"]\n'
        "}\n\n"
        "Rules:\n"
        "- Use ONLY URLs from the search results (do not invent links).\n"
        "- Include 3-5 budget_companies sorted by best budget fit.\n"
        "- stretch_companies: max 2 premium options if user budget is below vision tier.\n"
        "- estimated_range must be realistic for UAE and respect user budget where possible.\n"
        "- cost_saving_tips: 2-3 practical ways to reduce cost.\n\n"
        f"Requirements:\n{json.dumps(requirements, indent=2)}\n\n"
        f"Budget analysis:\n{json.dumps(budget_analysis, indent=2)}\n\n"
        f"Web search results:\n{json.dumps(search_results[:10], indent=2)}"
    )

    payload = {
        "model": GEMMA_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "Respond with JSON only. Never fabricate URLs.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
    }

    try:
        response = httpx.post(
            OPENROUTER_API_URL,
            headers=_openrouter_headers(),
            json=payload,
            timeout=75.0,
        )
        if response.status_code != 200:
            return None

        content = (
            response.json()["choices"][0]["message"].get("content") or ""
        ).strip()
        parsed = _parse_json_response(content)

        budget_companies = parsed.get("budget_companies") or []
        valid_urls = {item.get("url") for item in search_results if item.get("url")}
        valid_urls_normalized = {
            url.rstrip("/").lower(): url for url in valid_urls
        }

        def _resolve_url(candidate: str) -> str | None:
            candidate = candidate.rstrip("/").lower()
            return valid_urls_normalized.get(candidate)

        cleaned_budget = []
        for company in budget_companies:
            if not isinstance(company, dict):
                continue
            url = (company.get("url") or "").strip()
            name = (company.get("name") or "").strip()
            resolved = _resolve_url(url) if url else None
            if name and resolved:
                cleaned_budget.append(
                    {
                        "name": name,
                        "url": resolved,
                        "snippet": "",
                        "why_recommended": company.get("why_recommended") or "",
                        "estimated_range": company.get("estimated_range") or "",
                        "tier": company.get("tier") or "budget-friendly",
                    }
                )

        cleaned_stretch = []
        for company in parsed.get("stretch_companies") or []:
            if not isinstance(company, dict):
                continue
            url = (company.get("url") or "").strip()
            name = (company.get("name") or "").strip()
            resolved = _resolve_url(url) if url else None
            if name and resolved:
                cleaned_stretch.append(
                    {
                        "name": name,
                        "url": resolved,
                        "snippet": "",
                        "why_recommended": company.get("why_recommended") or "",
                        "estimated_range": company.get("estimated_range") or "",
                        "tier": "premium",
                    }
                )

        tips = parsed.get("cost_saving_tips") or []
        if not cleaned_budget:
            return None

        return {
            "budget_companies": cleaned_budget[:5],
            "stretch_companies": cleaned_stretch[:2],
            "cost_saving_tips": [str(t) for t in tips[:3]],
        }
    except Exception:
        return None

    return None


def extract_requirements_from_conversation(
    messages: list[dict],
    current: dict,
) -> dict:
    """Re-sync requirements from conversation using contextual parsing."""
    updated = {**current}

    for index, message in enumerate(messages):
        if message.get("role") == "user" and message.get("content"):
            updated = contextual_extract_from_turn(
                messages[:index],
                message["content"],
                updated,
            )

    return updated
