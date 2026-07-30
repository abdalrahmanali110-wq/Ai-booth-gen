from __future__ import annotations

import hashlib
import uuid
from typing import Any

from app.core.config import ANON_MAX_IMAGE_GENERATIONS
from app.core.database import supabase


def create_visitor(fingerprint: str | None = None) -> dict[str, Any]:
    fingerprint_hash = None
    if fingerprint:
        fingerprint_hash = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()

    response = (
        supabase.table("anonymous_visitors")
        .insert({"fingerprint_hash": fingerprint_hash})
        .execute()
    )
    return response.data[0]


def get_or_create_visitor(visitor_id: str | None, fingerprint: str | None = None) -> dict[str, Any]:
    if visitor_id:
        existing = (
            supabase.table("anonymous_visitors")
            .select("*")
            .eq("id", visitor_id)
            .execute()
        )
        if existing.data:
            return existing.data[0]
    return create_visitor(fingerprint)


def count_image_attempts(visitor_id: str | None = None, user_id: str | None = None) -> int:
    query = (
        supabase.table("generation_attempts")
        .select("id", count="exact")
        .eq("kind", "image")
    )
    if user_id:
        query = query.eq("user_id", user_id)
    elif visitor_id:
        query = query.eq("visitor_id", visitor_id)
    else:
        return 0

    response = query.execute()
    if response.count is not None:
        return int(response.count)
    return len(response.data or [])


def get_quota(visitor_id: str | None = None, user_id: str | None = None) -> dict[str, int]:
    # Authenticated users keep the same free cap for MVP unless claimed differently.
    used = count_image_attempts(visitor_id=visitor_id, user_id=user_id)
    max_attempts = ANON_MAX_IMAGE_GENERATIONS
    remaining = max(0, max_attempts - used)
    return {
        "used": used,
        "remaining": remaining,
        "max": max_attempts,
    }


def assert_can_generate(visitor_id: str | None = None, user_id: str | None = None) -> dict[str, int]:
    quota = get_quota(visitor_id=visitor_id, user_id=user_id)
    if quota["remaining"] <= 0:
        raise PermissionError(
            f"Free generation limit reached ({quota['max']} images). "
            "Sign in with Google anytime to save your project and unlock 3D conversion."
        )
    return quota


def record_image_attempt(
    *,
    session_id: str,
    visitor_id: str | None = None,
    user_id: str | None = None,
) -> None:
    supabase.table("generation_attempts").insert(
        {
            "visitor_id": visitor_id,
            "user_id": user_id,
            "session_id": session_id,
            "kind": "image",
        }
    ).execute()


def new_visitor_id() -> str:
    return str(uuid.uuid4())
