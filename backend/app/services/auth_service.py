from __future__ import annotations

from typing import Any

import httpx

from app.core.config import DEFAULT_USER_ID, SUPABASE_ANON_KEY, SUPABASE_KEY, SUPABASE_URL
from app.core.database import supabase


def extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, value = authorization.partition(" ")
    if scheme.lower() != "bearer" or not value.strip():
        return None
    return value.strip()


def verify_access_token(access_token: str) -> dict[str, Any]:
    """Validate a Supabase user JWT and return the auth user payload."""
    if not access_token or not str(access_token).strip():
        raise PermissionError("Missing access token")

    api_key = SUPABASE_ANON_KEY or SUPABASE_KEY
    if not SUPABASE_URL or not api_key:
        raise RuntimeError(
            "Supabase Auth is not configured (SUPABASE_URL / anon key)."
        )

    try:
        response = httpx.get(
            f"{SUPABASE_URL}/auth/v1/user",
            headers={
                "apikey": api_key,
                "Authorization": f"Bearer {access_token}",
            },
            timeout=30.0,
        )
    except Exception as exc:
        raise RuntimeError(f"Auth user lookup failed: {exc}") from exc

    body = response.json() if response.content else {}
    if response.status_code >= 400:
        message = body.get("msg") or body.get("message") or "Invalid or expired session"
        raise PermissionError(message)

    if not body.get("id"):
        raise PermissionError("OAuth user is missing id")
    return body


def require_authenticated_user(authorization: str | None) -> dict[str, Any]:
    token = extract_bearer_token(authorization)
    if not token:
        raise PermissionError("Sign in required. Missing Authorization Bearer token.")
    return verify_access_token(token)


def upsert_app_user(
    *,
    auth_user_id: str,
    email: str,
    name: str | None = None,
    phone: str | None = None,
    company: str | None = None,
) -> dict[str, Any]:
    existing = (
        supabase.table("users")
        .select("*")
        .eq("auth_user_id", auth_user_id)
        .execute()
    )
    payload = {
        "auth_user_id": auth_user_id,
        "email": email,
        "full_name": name,
        "phone": phone,
        "company": company,
        "company_name": company,
    }

    if existing.data:
        response = (
            supabase.table("users")
            .update(payload)
            .eq("auth_user_id", auth_user_id)
            .execute()
        )
        return response.data[0]

    # users.id historically required; use auth uuid as primary key when possible
    payload["id"] = auth_user_id
    try:
        response = supabase.table("users").insert(payload).execute()
        return response.data[0]
    except Exception:
        # Fallback without forcing id if schema differs
        payload.pop("id", None)
        response = supabase.table("users").insert(payload).execute()
        return response.data[0]


def create_lead(
    *,
    email: str,
    name: str | None = None,
    phone: str | None = None,
    company: str | None = None,
    session_id: str | None = None,
    user_id: str | None = None,
    auth_user_id: str | None = None,
) -> dict[str, Any]:
    response = (
        supabase.table("leads")
        .insert(
            {
                "email": email,
                "name": name,
                "phone": phone,
                "company": company,
                "session_id": session_id,
                "user_id": user_id,
                "auth_user_id": auth_user_id,
            }
        )
        .execute()
    )
    return response.data[0]


def claim_session(
    *,
    session_id: str,
    auth_user_id: str,
    visitor_id: str | None = None,
) -> dict[str, Any]:
    session_resp = (
        supabase.table("chat_sessions").select("*").eq("id", session_id).execute()
    )
    if not session_resp.data:
        raise ValueError("Session not found")

    session = session_resp.data[0]
    if visitor_id and session.get("visitor_id") and session["visitor_id"] != visitor_id:
        raise PermissionError("Session does not belong to this visitor")

    response = (
        supabase.table("chat_sessions")
        .update(
            {
                "claimed_user_id": auth_user_id,
                "user_id": auth_user_id,
                "anon": False,
            }
        )
        .eq("id", session_id)
        .execute()
    )
    return response.data[0]


def auth_public_config() -> dict[str, str | None]:
    return {
        "supabase_url": SUPABASE_URL,
        "supabase_anon_key": SUPABASE_ANON_KEY,
        "default_user_id": DEFAULT_USER_ID,
    }
