from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException

from app.models.auth import LoginRequest, OAuthCompleteRequest, SignupRequest
from app.services.auth_service import (
    auth_public_config,
    claim_session,
    create_lead,
    upsert_app_user,
    verify_access_token,
)

router = APIRouter()


@router.get("/config")
def get_auth_config():
    return {
        "success": True,
        **auth_public_config(),
        "providers": ["google"],
    }


@router.post("/oauth/complete")
def oauth_complete(
    data: OAuthCompleteRequest,
    x_visitor_id: str | None = Header(default=None, alias="X-Visitor-Id"),
):
    """Finalize Google (or other OAuth) login after the browser receives a Supabase session."""
    if not data.access_token:
        raise HTTPException(status_code=400, detail="Missing access token")

    try:
        body = verify_access_token(data.access_token)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    auth_user_id = body.get("id")
    email = body.get("email")
    meta = body.get("user_metadata") or {}
    name = (
        data.name
        or meta.get("full_name")
        or meta.get("name")
        or meta.get("preferred_username")
    )

    if not auth_user_id or not email:
        raise HTTPException(status_code=400, detail="OAuth user is missing id or email")

    app_user = upsert_app_user(
        auth_user_id=auth_user_id,
        email=email,
        name=name,
        phone=data.phone,
        company=data.company,
    )

    lead = create_lead(
        email=email,
        name=name,
        phone=data.phone,
        company=data.company,
        session_id=data.session_id,
        user_id=app_user.get("id"),
        auth_user_id=auth_user_id,
    )

    claimed = None
    if data.session_id:
        try:
            claimed = claim_session(
                session_id=data.session_id,
                auth_user_id=auth_user_id,
                visitor_id=x_visitor_id,
            )
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {
        "success": True,
        "user": app_user,
        "auth": {
            "access_token": data.access_token,
            "auth_user_id": auth_user_id,
            "email": email,
            "name": name,
        },
        "lead": lead,
        "session": claimed,
    }


@router.post("/signup")
def signup(
    data: SignupRequest,
    x_visitor_id: str | None = Header(default=None, alias="X-Visitor-Id"),
):
    raise HTTPException(
        status_code=400,
        detail="Email signup is disabled. Use Google sign-in instead.",
    )


@router.post("/login")
def login(
    data: LoginRequest,
    x_visitor_id: str | None = Header(default=None, alias="X-Visitor-Id"),
):
    raise HTTPException(
        status_code=400,
        detail="Email login is disabled. Use Google sign-in instead.",
    )

