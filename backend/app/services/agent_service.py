import json
from typing import Any

from app.core.config import DEFAULT_USER_ID
from app.core.database import supabase
from app.models.chat import DEFAULT_SESSION_TITLE
from app.services.consultation_report_service import generate_consultation_report
from app.services.gemma_service import (
    chat_reply,
    contextual_extract_from_turn,
    extract_requirements_from_conversation,
    summarize_known_requirements,
)
from app.services.consultant_config import (
    build_consultant_system_prompt,
    user_confirmed_generation,
)
from app.providers.registry import get_llm_provider
from app.providers.base import ProviderNotConfigured
from app.services.image_service import generate_booth_image

from app.services.budget_service import calculate_budget

REQUIRED_FIELDS = [
    "brand_name",
    "industry",
    "event_name",
    "location",
    "booth_size",
    "open_sides",
    "theme",
    "brand_colors",
    "special_requirements",
    "budget",
]

AUTO_TITLE_PLACEHOLDERS = {
    "",
    DEFAULT_SESSION_TITLE,
    "Booth consultation",
    "Booth studio",
}


def empty_requirements() -> dict[str, Any]:
    return {
        "brand_name": None,
        "industry": None,
        "event_name": None,
        "booth_size": None,
        "budget": None,
        "theme": None,
        "location": None,
        "open_sides": None,
        "brand_colors": None,
        "slogan": None,
        "event_date": None,
        "special_requirements": None,
    }


def get_requirements(session_id: str) -> dict[str, Any]:
    response = (
        supabase.table("booth_requirements")
        .select("*")
        .eq("session_id", session_id)
        .execute()
    )

    if not response.data:
        return empty_requirements()

    row = response.data[0]
    special = row.get("special_requirements")
    if special == [] and not any(row.get(field) for field in REQUIRED_FIELDS if field != "special_requirements"):
        special = None

    return {
        "brand_name": row.get("brand_name"),
        "industry": row.get("industry"),
        "event_name": row.get("event_name"),
        "booth_size": row.get("booth_size"),
        "budget": row.get("budget"),
        "theme": row.get("theme"),
        "location": row.get("location"),
        "open_sides": row.get("open_sides"),
        "brand_colors": row.get("brand_colors"),
        "slogan": row.get("slogan"),
        "event_date": row.get("event_date"),
        "special_requirements": special,
    }


def _requirements_payload(
    session_id: str,
    requirements: dict[str, Any],
    *,
    include_optional: bool = True,
) -> dict[str, Any]:
    payload = {
        "session_id": session_id,
        "industry": requirements.get("industry"),
        "event_name": requirements.get("event_name"),
        "booth_size": requirements.get("booth_size"),
        "budget": requirements.get("budget"),
        "theme": requirements.get("theme"),
        "location": requirements.get("location"),
        "special_requirements": requirements.get("special_requirements"),
        "brand_name": requirements.get("brand_name"),
        "open_sides": requirements.get("open_sides"),
        "brand_colors": requirements.get("brand_colors"),
        "slogan": requirements.get("slogan"),
        "event_date": requirements.get("event_date"),
    }

    if include_optional and requirements.get("booth_request_id"):
        payload["booth_request_id"] = requirements.get("booth_request_id")

    return payload


def maybe_update_session_title(
    session_id: str,
    requirements: dict[str, Any],
) -> None:
    event_name = (requirements.get("event_name") or "").strip()
    if not event_name:
        return

    try:
        session_response = (
            supabase.table("chat_sessions")
            .select("title")
            .eq("id", session_id)
            .execute()
        )
        if not session_response.data:
            return

        current_title = (session_response.data[0].get("title") or "").strip()
        if current_title not in AUTO_TITLE_PLACEHOLDERS:
            return

        supabase.table("chat_sessions").update(
            {"title": event_name}
        ).eq("id", session_id).execute()
    except Exception:
        pass


def save_requirements(session_id: str, requirements: dict[str, Any]) -> None:
    existing = (
        supabase.table("booth_requirements")
        .select("id")
        .eq("session_id", session_id)
        .execute()
    )

    payload = _requirements_payload(session_id, requirements)

    try:
        if existing.data:
            supabase.table("booth_requirements").update(payload).eq(
                "session_id", session_id
            ).execute()
        else:
            supabase.table("booth_requirements").insert(payload).execute()
    except Exception:
        # Fallback if migration 009 columns are not applied yet
        legacy = {
            "session_id": session_id,
            "industry": requirements.get("industry"),
            "event_name": requirements.get("event_name"),
            "booth_size": requirements.get("booth_size"),
            "budget": requirements.get("budget"),
            "theme": requirements.get("theme"),
            "location": requirements.get("location"),
            "special_requirements": requirements.get("special_requirements"),
        }
        extras = []
        for key, label in (
            ("brand_name", "Brand"),
            ("open_sides", "Open sides"),
            ("brand_colors", "Colors"),
            ("slogan", "Slogan"),
            ("event_date", "Event date"),
        ):
            value = requirements.get(key)
            if value:
                extras.append(f"{label}: {value}")
        if extras:
            features = legacy.get("special_requirements") or []
            if not isinstance(features, list):
                features = [str(features)]
            legacy["special_requirements"] = extras + list(features)

        if existing.data:
            supabase.table("booth_requirements").update(legacy).eq(
                "session_id", session_id
            ).execute()
        else:
            supabase.table("booth_requirements").insert(legacy).execute()


def get_next_question(requirements: dict[str, Any]) -> str | None:
    if not requirements.get("brand_name"):
        return "What's your brand name?"

    if not requirements.get("industry"):
        return (
            "What industry are you in? "
            "Fashion / Tech / Automotive / Food & Beverage / Jewelry / "
            "Government / Finance / Other"
        )

    if requirements.get("slogan") is None:
        return "What's your slogan or tagline? (optional — say skip if none)"

    if not requirements.get("event_name"):
        return "What's the event name?"

    if not requirements.get("location"):
        return "Where is the event located? (city or venue)"

    if requirements.get("event_date") is None:
        return "What's the event date? (optional — say skip if you don't know yet)"

    if not requirements.get("booth_size"):
        return (
            "What booth size do you need? "
            "3x3 / 4x4 / 6x6 / 9x9 / Custom (enter dimensions)"
        )

    if not requirements.get("open_sides"):
        return (
            "How many open sides? "
            "1 side / 2 sides (corner) / 3 sides / All sides (open on every side)"
        )

    if not requirements.get("theme"):
        return (
            "What direction do you want the design to feel? "
            "Premium & Luxury / Modern & Tech / Minimal & Clean / "
            "Bold & Playful / Traditional & Elegant"
        )

    if not requirements.get("brand_colors"):
        return "What are your brand colors?"

    if requirements.get("special_requirements") is None:
        return (
            "What do you want inside your booth? You can pick several: "
            "Counter / Reception desk / Meeting room / Storage room / "
            "LED screens / Hanging sign / Seating area / Product shelves "
            "(or say none)"
        )

    if not requirements.get("budget"):
        return (
            "What's your budget range in AED? "
            "Under 40,000 / 40,000–90,000 / 90,000–180,000 / 180,000+"
        )

    return None


def is_complete(requirements: dict[str, Any]) -> bool:
    for field in REQUIRED_FIELDS:
        if field == "special_requirements":
            if requirements.get("special_requirements") is None:
                return False
            continue
        if not requirements.get(field):
            return False
    return get_next_question(requirements) is None


def get_missing_fields(requirements: dict[str, Any]) -> list[str]:
    missing = []
    for field in REQUIRED_FIELDS:
        if field == "special_requirements":
            if requirements.get("special_requirements") is None:
                missing.append(field)
        elif not requirements.get(field):
            missing.append(field)
    return missing


def build_booth_prompt(requirements: dict[str, Any]) -> str:
    special = requirements.get("special_requirements") or []
    if isinstance(special, list):
        special = ", ".join(str(item) for item in special)
    brand = requirements.get("brand_name") or "the brand"
    colors = requirements.get("brand_colors") or "brand colors"
    open_sides = requirements.get("open_sides") or "standard sides"
    slogan = requirements.get("slogan") or ""
    slogan_bit = f' slogan "{slogan}",' if slogan and slogan.lower() != "skip" else ""
    return (
        f"Luxury {requirements['industry']} exhibition booth for {brand} at "
        f"{requirements['event_name']} in {requirements['location']}, "
        f"{requirements['theme']} design direction,{slogan_bit} "
        f"brand colors {colors}, booth size {requirements['booth_size']}, "
        f"open sides: {open_sides}, budget tier {requirements['budget']} AED, "
        f"interior features: {special or 'reception and display'}, "
        f"professional trade show stand, photorealistic architectural "
        f"visualization, ultra realistic, 8k"
    )


def get_conversation_history(session_id: str) -> list[dict]:
    try:
        response = (
            supabase.table("chat_messages")
            .select("role, message, reasoning_details")
            .eq("session_id", session_id)
            .order("created_at")
            .execute()
        )
    except Exception:
        response = (
            supabase.table("chat_messages")
            .select("role, message")
            .eq("session_id", session_id)
            .order("created_at")
            .execute()
        )

    messages = []
    for row in response.data:
        message = {
            "role": row["role"],
            "content": row["message"],
        }
        if row["role"] == "assistant" and row.get("reasoning_details"):
            message["reasoning_details"] = row["reasoning_details"]
        messages.append(message)

    return messages


def _dedupe_conversation(messages: list[dict]) -> list[dict]:
    if not messages:
        return messages

    deduped = [messages[0]]
    for message in messages[1:]:
        prev = deduped[-1]
        if (
            message.get("role") == prev.get("role")
            and message.get("content") == prev.get("content")
        ):
            continue
        deduped.append(message)

    return deduped


def generate_agent_reply(session_id: str, user_message: str) -> dict[str, Any]:
    history = _dedupe_conversation(get_conversation_history(session_id))

    requirements = extract_requirements_from_conversation(
        history,
        empty_requirements(),
    )
    # Ensure the latest user turn is always extracted, even if history lag/dedupe
    # skipped it somehow.
    requirements = contextual_extract_from_turn(
        history,
        user_message,
        requirements,
    )

    complete = is_complete(requirements)
    missing = get_missing_fields(requirements)
    next_question = get_next_question(requirements)
    awaiting_confirmation = complete and not user_confirmed_generation(user_message)
    should_generate = complete and user_confirmed_generation(user_message)
    known_summary = summarize_known_requirements(requirements)

    filled = {
        key: value
        for key, value in requirements.items()
        if value not in (None, "", [])
    }

    reasoning_details = None
    reply = None

    # Prefer LLM consultant guided by booth designer config.
    try:
        provider = get_llm_provider()
        system_prompt = build_consultant_system_prompt()
        context = (
            f"Already collected requirements (NEVER ask these again):\n"
            f"{json.dumps(filled, indent=2)}\n\n"
            f"Still missing fields: {', '.join(missing) if missing else 'none'}\n"
            f"Known summary: {known_summary or 'nothing yet'}\n"
        )
        if awaiting_confirmation:
            context += (
                "All required fields appear collected. Briefly acknowledge that the "
                "project summary is ready for review. Do NOT ask them to type yes or "
                "looks good — the UI shows a summary popup with a Generate button."
            )
        elif next_question:
            context += (
                "The UI already shows an answer card for the next missing field. "
                "Your chat message must ONLY acknowledge what you already extracted "
                "from the user's latest message, then invite them to answer the card. "
                "Do NOT repeat the card question verbatim. "
                "Do NOT ask about any already-collected field. "
                f"Next missing field hint (for you only, do not copy): {next_question}"
            )

        # Avoid duplicating the latest user message if it is already in history.
        history_payload = [
            {"role": m["role"], "content": m["content"]} for m in history
        ]
        if not history_payload or history_payload[-1].get("content") != user_message:
            history_payload.append({"role": "user", "content": user_message})

        llm_messages = [
            *history_payload,
            {"role": "system", "content": context},
        ]
        result = provider.chat(
            llm_messages,
            system_prompt=system_prompt,
            temperature=0.4,
        )
        reply = result.content
        reasoning_details = result.reasoning_details
    except (ProviderNotConfigured, Exception):
        reply = None

    if not reply:
        if awaiting_confirmation:
            reply = (
                "Your booth brief is ready. Review the summary popup, edit anything "
                "you want, then tap Generate concept."
            )
        elif not complete and next_question:
            if known_summary:
                reply = (
                    f"Got it — {known_summary}. "
                    "I'd like a few more details about your booth."
                )
            else:
                reply = "I'd like to know a few details about your booth."
        else:
            fallback = chat_reply(
                history,
                user_message,
                requirements,
                next_question=next_question,
            )
            reply = (fallback or {}).get("reply") or (
                f"Got it — {known_summary}."
                if known_summary
                else "Tell me more about the booth you want to build."
            )

    # Guardrail: if the model re-asks something already known, replace with adaptive ack.
    if reply and filled and not awaiting_confirmation:
        lower_reply = reply.lower()
        reasked = False
        ask_markers = {
            "brand_name": ["brand name", "what's your brand"],
            "industry": ["what industry", "which industry"],
            "booth_size": ["booth size", "what size"],
            "theme": ["design to feel", "what direction", "theme"],
            "event_name": ["event name", "what's the event"],
            "location": ["where is the event", "located"],
            "brand_colors": ["brand colors", "brand colours"],
            "budget": ["budget range", "what's your budget"],
            "open_sides": ["open sides", "how many open"],
        }
        for field, markers in ask_markers.items():
            if requirements.get(field) and any(marker in lower_reply for marker in markers):
                reasked = True
                break
        if reasked:
            reply = (
                f"Got it — {known_summary}. "
                "I'd like a few more details about your booth."
                if known_summary
                else "I'd like a few more details about your booth."
            )

    save_requirements(session_id, requirements)
    maybe_update_session_title(session_id, requirements)

    # Never claim generation unless the backend will actually run it.
    jumped_to_generation = any(
        phrase in (reply or "").lower()
        for phrase in [
            "generating booth",
            "starting booth generation",
            "starting booth image",
            "generate your booth",
            "create your booth",
        ]
    )
    if jumped_to_generation and not should_generate:
        if not complete:
            reply = (
                f"Got it — {known_summary}. "
                "I'd like a few more details about your booth."
                if known_summary
                else "I'd like a few more details about your booth."
            )
        else:
            reply = (
                "Your booth brief is ready. Review the summary popup and tap "
                "Generate concept when you're happy with it."
            )

    return {
        "reply": reply,
        "reasoning_details": reasoning_details,
        "requirements": requirements,
        "requirements_complete": complete,
        "awaiting_confirmation": awaiting_confirmation,
        "missing_fields": missing,
        "should_generate": should_generate,
    }


def run_generation_pipeline(session_id: str) -> dict[str, Any]:
    requirements = get_requirements(session_id)

    if not is_complete(requirements):
        missing = get_missing_fields(requirements)
        raise ValueError(
            f"Requirements incomplete. Missing: {', '.join(missing)}"
        )

    prompt = build_booth_prompt(requirements)
    image_result = generate_booth_image(prompt)

    booth_response = supabase.table("booth_requests").insert(
        {
            "user_id": DEFAULT_USER_ID,
            "industry": requirements["industry"],
            "booth_theme": requirements["theme"],
            "booth_size": requirements["booth_size"],
            "colors": requirements.get("theme"),
            "prompt": prompt,
            "status": "completed",
        }
    ).execute()

    booth_record = booth_response.data[0]
    booth_id = booth_record["id"]

    image_response = supabase.table("generated_images").insert(
        {
            "booth_request_id": booth_id,
            "image_url": image_result["image_url"],
            "image_provider": image_result["provider"],
            "prompt_used": prompt,
        }
    ).execute()

    consultation_report = generate_consultation_report(requirements)
    suppliers_data = (
        consultation_report.get("web_companies") or []
    ) + (consultation_report.get("stretch_companies") or [])
    saved_suppliers = []

    for supplier in suppliers_data:
        supplier_response = supabase.table("supplier_recommendations").insert(
            {
                "booth_request_id": booth_id,
                "company_name": supplier["name"],
                "website_url": supplier.get("url"),
                "location": requirements.get("location") or "Dubai",
                "description": (
                    f"{supplier.get('why_recommended') or supplier.get('snippet', '')} "
                    f"{supplier.get('estimated_range', '')}".strip()
                ),
                "source": f"web-{supplier.get('tier', 'recommended')}",
            }
        ).execute()
        saved_suppliers.append(supplier_response.data[0])

    budget_analysis = consultation_report["budget_analysis"]
    build_cost = (
        budget_analysis["user_budget"]
        if budget_analysis["user_budget"]
        else budget_analysis["market_range_high"]
    )
    budget = calculate_budget(
        [{"estimated_cost": build_cost}],
        requirements["booth_size"],
    )

    proposal_text = consultation_report["markdown"]

    proposal_response = supabase.table("project_proposals").insert(
        {
            "booth_request_id": booth_id,
            "proposal_title": (
                f"{requirements['event_name']} Exhibition Proposal"
            ),
            "proposal_summary": proposal_text,
            "estimated_budget": budget["grand_total"],
        }
    ).execute()

    try:
        supabase.table("chat_sessions").update(
            {
                "status": "completed",
                "booth_request_id": booth_id,
            }
        ).eq("id", session_id).execute()
    except Exception:
        pass

    supabase.table("booth_requirements").update(
        {"booth_request_id": booth_id}
    ).eq("session_id", session_id).execute()

    return {
        "booth_request": booth_record,
        "generated_image": image_response.data[0],
        "suppliers": saved_suppliers,
        "budget": budget,
        "proposal": proposal_response.data[0],
        "consultation_report": consultation_report,
        "requirements": requirements,
    }


def get_session_generation_result(session_id: str) -> dict[str, Any] | None:
    session_response = (
        supabase.table("chat_sessions")
        .select("booth_request_id")
        .eq("id", session_id)
        .execute()
    )

    if not session_response.data:
        return None

    booth_request_id = session_response.data[0].get("booth_request_id")

    if not booth_request_id:
        requirements_response = (
            supabase.table("booth_requirements")
            .select("booth_request_id")
            .eq("session_id", session_id)
            .execute()
        )
        if requirements_response.data:
            booth_request_id = requirements_response.data[0].get("booth_request_id")

    if not booth_request_id:
        return None

    booth_response = (
        supabase.table("booth_requests")
        .select("*")
        .eq("id", booth_request_id)
        .execute()
    )
    if not booth_response.data:
        return None

    booth_record = booth_response.data[0]

    image_response = (
        supabase.table("generated_images")
        .select("*")
        .eq("booth_request_id", booth_request_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not image_response.data:
        return None

    suppliers_response = (
        supabase.table("supplier_recommendations")
        .select("*")
        .eq("booth_request_id", booth_request_id)
        .execute()
    )

    proposal_response = (
        supabase.table("project_proposals")
        .select("*")
        .eq("booth_request_id", booth_request_id)
        .limit(1)
        .execute()
    )

    proposal = proposal_response.data[0] if proposal_response.data else None
    requirements = get_requirements(session_id)
    consultation_report = (
        generate_consultation_report(
            requirements,
            saved_suppliers=suppliers_response.data,
            skip_web_search=True,
        )
        if proposal
        else None
    )
    budget = None
    if proposal and proposal.get("estimated_budget") is not None:
        budget = {"grand_total": proposal["estimated_budget"]}

    return {
        "booth_request": booth_record,
        "generated_image": image_response.data[0],
        "suppliers": suppliers_response.data or [],
        "budget": budget,
        "proposal": proposal,
        "consultation_report": consultation_report,
        "requirements": requirements,
    }
