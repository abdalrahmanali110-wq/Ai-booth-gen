from typing import Any

from app.core.config import DEFAULT_USER_ID
from app.core.database import supabase
from app.models.chat import DEFAULT_SESSION_TITLE
from app.services.consultation_report_service import generate_consultation_report
from app.services.gemma_service import (
    chat_reply,
    extract_requirements_from_conversation,
)
from app.services.image_service import generate_booth_image

from app.services.budget_service import calculate_budget

REQUIRED_FIELDS = [
    "industry",
    "event_name",
    "booth_size",
    "budget",
    "theme",
    "location",
]

AUTO_TITLE_PLACEHOLDERS = {
    "",
    DEFAULT_SESSION_TITLE,
    "Booth consultation",
}


def empty_requirements() -> dict[str, Any]:
    return {
        "industry": None,
        "event_name": None,
        "booth_size": None,
        "budget": None,
        "theme": None,
        "location": None,
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
    if special == [] and not any(
        row.get(field) for field in REQUIRED_FIELDS
    ):
        special = None

    return {
        "industry": row.get("industry"),
        "event_name": row.get("event_name"),
        "booth_size": row.get("booth_size"),
        "budget": row.get("budget"),
        "theme": row.get("theme"),
        "location": row.get("location"),
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
        payload = _requirements_payload(
            session_id,
            requirements,
            include_optional=False,
        )
        if existing.data:
            supabase.table("booth_requirements").update(payload).eq(
                "session_id", session_id
            ).execute()
        else:
            supabase.table("booth_requirements").insert(payload).execute()


def get_next_question(requirements: dict[str, Any]) -> str | None:
    if not requirements.get("industry"):
        return "What industry are you in?"

    if not requirements.get("event_name"):
        return "What event or exhibition will you attend?"

    if not requirements.get("booth_size"):
        return "What booth size do you need? (e.g. 3x3, 6x6, 12x12)"

    if not requirements.get("budget"):
        return "What is your budget in AED?"

    if not requirements.get("theme"):
        return "What theme or style do you prefer for your booth?"

    if not requirements.get("location"):
        return "In which city will the event take place?"

    if requirements.get("special_requirements") is None:
        return "Any special requirements for your booth? (or say none)"

    return None


def is_complete(requirements: dict[str, Any]) -> bool:
    for field in REQUIRED_FIELDS:
        if not requirements.get(field):
            return False
    return get_next_question(requirements) is None


def get_missing_fields(requirements: dict[str, Any]) -> list[str]:
    missing = [
        field
        for field in REQUIRED_FIELDS
        if not requirements.get(field)
    ]
    if requirements.get("special_requirements") is None:
        missing.append("special_requirements")
    return missing


def build_booth_prompt(requirements: dict[str, Any]) -> str:
    special = requirements.get("special_requirements") or []
    if isinstance(special, list):
        special = ", ".join(special)
    return (
        f"Luxury {requirements['industry']} exhibition booth at "
        f"{requirements['event_name']} in {requirements['location']}, "
        f"{requirements['theme']} design, booth size {requirements['booth_size']}, "
        f"budget tier {requirements['budget']} AED, "
        f"features: {special}, "
        f"professional trade show stand, LED walls, branding panels, "
        f"reception counter, meeting lounge, product displays, "
        f"photorealistic architectural visualization, ultra realistic, 8k"
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

    complete = is_complete(requirements)
    missing = get_missing_fields(requirements)
    next_question = get_next_question(requirements)

    reasoning_details = None
    reply = None

    if not complete and next_question:
        reply = next_question
    else:
        llm_result = chat_reply(
            history,
            user_message,
            requirements,
            next_question=next_question,
        )
        if llm_result:
            reply = llm_result.get("reply")
            reasoning_details = llm_result.get("reasoning_details")

    save_requirements(session_id, requirements)
    maybe_update_session_title(session_id, requirements)

    if not reply:
        reply = next_question or (
            "Great, I have everything I need. Starting booth generation now."
        )

    jumped_to_generation = any(
        phrase in (reply or "").lower()
        for phrase in [
            "generating booth",
            "starting booth generation",
            "generate your booth",
            "create your booth",
        ]
    )

    if jumped_to_generation and not complete:
        next_question = get_next_question(requirements)
        reply = (
            f"I still need a few details before image generation. "
            f"{next_question}"
        )
    elif complete:
        reply = (
            "Great, I have everything I need. "
            "Starting booth image generation now..."
        )

    return {
        "reply": reply,
        "reasoning_details": reasoning_details,
        "requirements": requirements,
        "requirements_complete": complete,
        "missing_fields": missing,
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
