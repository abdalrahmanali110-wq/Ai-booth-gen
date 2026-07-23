from datetime import datetime, timezone
from typing import Any

from app.core.config import DEFAULT_USER_ID
from app.core.database import supabase
from app.services.image_service import generate_booth_image
from app.services.prompt_compiler import compile_prompt, validate_answers
from app.services.questionnaire_config import (
    MAX_REGENERATIONS,
    OTHER_TEXT_MAX_LENGTH,
    get_questions_public,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sanitize_answers(answers: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}

    for key, raw in (answers or {}).items():
        if not isinstance(raw, dict):
            continue

        value = raw.get("value")
        other = (raw.get("other_text") or "").strip()
        if len(other) > OTHER_TEXT_MAX_LENGTH:
            other = other[:OTHER_TEXT_MAX_LENGTH]

        entry: dict[str, Any] = {"value": value}
        if other:
            entry["other_text"] = other
        cleaned[key] = entry

    return cleaned


def create_design_session(title: str = "Booth Design") -> dict[str, Any]:
    response = (
        supabase.table("booth_designs")
        .insert(
            {
                "user_id": DEFAULT_USER_ID,
                "title": title,
                "status": "in_progress",
                "answers": {},
                "regenerate_count": 0,
            }
        )
        .execute()
    )
    return response.data[0]


def get_design_session(session_id: str) -> dict[str, Any] | None:
    response = (
        supabase.table("booth_designs")
        .select("*")
        .eq("id", session_id)
        .execute()
    )
    if not response.data:
        return None
    return response.data[0]


def list_design_sessions(limit: int = 50) -> list[dict[str, Any]]:
    response = (
        supabase.table("booth_designs")
        .select(
            "id, title, status, image_url, regenerate_count, created_at, updated_at"
        )
        .eq("user_id", DEFAULT_USER_ID)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return response.data or []


def save_answers(session_id: str, answers: dict[str, Any]) -> dict[str, Any]:
    session = get_design_session(session_id)
    if not session:
        raise ValueError("Session not found")

    merged = {**(session.get("answers") or {}), **sanitize_answers(answers)}

    response = (
        supabase.table("booth_designs")
        .update(
            {
                "answers": merged,
                "updated_at": _now_iso(),
                "status": "in_progress",
            }
        )
        .eq("id", session_id)
        .execute()
    )
    return response.data[0]


def generate_design(session_id: str) -> dict[str, Any]:
    session = get_design_session(session_id)
    if not session:
        raise ValueError("Session not found")

    answers = session.get("answers") or {}
    missing = validate_answers(answers)
    if missing:
        raise ValueError(
            f"Incomplete answers. Missing or invalid: {', '.join(missing)}"
        )

    prompt = compile_prompt(answers)
    image_result = generate_booth_image(prompt)

    response = (
        supabase.table("booth_designs")
        .update(
            {
                "compiled_prompt": prompt,
                "image_url": image_result["image_url"],
                "image_provider": image_result.get("provider"),
                "status": "completed",
                "updated_at": _now_iso(),
            }
        )
        .eq("id", session_id)
        .execute()
    )

    return {
        "session": response.data[0],
        "image_url": image_result["image_url"],
        "compiled_prompt": prompt,
        "provider": image_result.get("provider"),
    }


def regenerate_design(session_id: str) -> dict[str, Any]:
    session = get_design_session(session_id)
    if not session:
        raise ValueError("Session not found")

    count = int(session.get("regenerate_count") or 0)
    if count >= MAX_REGENERATIONS:
        raise ValueError(
            f"Regeneration limit reached ({MAX_REGENERATIONS} per session)."
        )

    prompt = session.get("compiled_prompt")
    if not prompt:
        answers = session.get("answers") or {}
        missing = validate_answers(answers)
        if missing:
            raise ValueError("No compiled prompt available. Complete answers first.")
        prompt = compile_prompt(answers)

    image_result = generate_booth_image(prompt)

    response = (
        supabase.table("booth_designs")
        .update(
            {
                "compiled_prompt": prompt,
                "image_url": image_result["image_url"],
                "image_provider": image_result.get("provider"),
                "regenerate_count": count + 1,
                "status": "completed",
                "updated_at": _now_iso(),
            }
        )
        .eq("id", session_id)
        .execute()
    )

    return {
        "session": response.data[0],
        "image_url": image_result["image_url"],
        "compiled_prompt": prompt,
        "regenerate_count": count + 1,
        "regenerations_remaining": MAX_REGENERATIONS - (count + 1),
        "provider": image_result.get("provider"),
    }


def save_lead(session_id: str, contact: dict[str, Any]) -> dict[str, Any]:
    session = get_design_session(session_id)
    if not session:
        raise ValueError("Session not found")

    name = (contact.get("name") or "").strip()
    email = (contact.get("email") or "").strip()
    phone = (contact.get("phone") or "").strip() or None

    if not name or not email:
        raise ValueError("Name and email are required")

    response = (
        supabase.table("booth_designs")
        .update(
            {
                "contact": {
                    "name": name,
                    "email": email,
                    "phone": phone,
                },
                "updated_at": _now_iso(),
            }
        )
        .eq("id", session_id)
        .execute()
    )
    return response.data[0]


def questions_payload() -> dict[str, Any]:
    return {
        "questions": get_questions_public(),
        "max_regenerations": MAX_REGENERATIONS,
        "other_text_max_length": OTHER_TEXT_MAX_LENGTH,
    }
