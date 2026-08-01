from fastapi import APIRouter, Header, HTTPException

from app.core.config import DEFAULT_USER_ID
from app.core.database import supabase
from app.models.chat import (
    CreateSessionRequest,
    ChatMessageRequest,
    UpdateRequirementsRequest,
    UpdateSessionRequest,
)
from app.services.agent_service import (
    generate_agent_reply,
    get_requirements,
    get_session_generation_result,
    is_complete,
    run_generation_pipeline,
    save_requirements,
)
from app.services.visitor_service import (
    assert_can_generate,
    get_or_create_visitor,
    get_quota,
    record_image_attempt,
)

router = APIRouter()


WELCOME_MESSAGE = (
    "Hello! I am your AI Booth Designer. "
    "Pick a starter idea below or tell me what you want — "
    "for example: \"Design a 6x6 fashion booth\"."
)


def _resolve_visitor(x_visitor_id: str | None) -> dict:
    try:
        return get_or_create_visitor(x_visitor_id)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Failed to resolve visitor: {exc}. "
                "Run database/migrations/008_lead_gen_3d.sql in Supabase."
            ),
        ) from exc


def _session_owned(session: dict, visitor_id: str | None) -> bool:
    if not visitor_id:
        return True
    session_visitor = session.get("visitor_id")
    if not session_visitor:
        return True
    return str(session_visitor) == str(visitor_id)


@router.get("/sessions")
def list_sessions(
    limit: int = 50,
    x_visitor_id: str | None = Header(default=None, alias="X-Visitor-Id"),
    x_auth_user_id: str | None = Header(default=None, alias="X-Auth-User-Id"),
):
    visitor = _resolve_visitor(x_visitor_id)

    # History is a signed-in feature — anonymous work stays off the sidebar.
    if not x_auth_user_id:
        return {
            "success": True,
            "sessions": [],
            "visitor_id": visitor["id"],
            "quota": get_quota(visitor_id=visitor["id"]),
            "history_locked": True,
        }

    sessions = []
    try:
        response = (
            supabase.table("chat_sessions")
            .select(
                "id, title, status, created_at, booth_request_id, visitor_id, anon, claimed_user_id"
            )
            .eq("claimed_user_id", x_auth_user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        sessions = response.data or []
    except Exception:
        try:
            response = (
                supabase.table("chat_sessions")
                .select("id, title, status, created_at, booth_request_id")
                .eq("user_id", x_auth_user_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            sessions = response.data or []
        except Exception:
            sessions = []

    return {
        "success": True,
        "sessions": sessions,
        "visitor_id": visitor["id"],
        "quota": get_quota(visitor_id=visitor["id"]),
        "history_locked": False,
    }


@router.get("/quota")
def chat_quota(
    x_visitor_id: str | None = Header(default=None, alias="X-Visitor-Id"),
):
    visitor = _resolve_visitor(x_visitor_id)
    return {
        "success": True,
        "visitor_id": visitor["id"],
        "quota": get_quota(visitor_id=visitor["id"]),
    }


@router.post("/session")
def create_session(
    data: CreateSessionRequest,
    x_visitor_id: str | None = Header(default=None, alias="X-Visitor-Id"),
    x_auth_user_id: str | None = Header(default=None, alias="X-Auth-User-Id"),
):
    visitor = _resolve_visitor(x_visitor_id)
    session = None
    last_error = None
    signed_in = bool(x_auth_user_id)

    for attempt in range(3):
        try:
            payload = {
                "user_id": x_auth_user_id if signed_in else DEFAULT_USER_ID,
                "title": data.title,
                "visitor_id": visitor["id"],
                "anon": not signed_in,
            }
            if signed_in:
                payload["claimed_user_id"] = x_auth_user_id
            response = supabase.table("chat_sessions").insert(payload).execute()
            session = response.data[0]
            break
        except Exception as exc:
            last_error = exc
            if attempt == 1:
                try:
                    response = (
                        supabase.table("chat_sessions")
                        .insert(
                            {
                                "user_id": (
                                    x_auth_user_id if signed_in else DEFAULT_USER_ID
                                ),
                                "title": data.title,
                            }
                        )
                        .execute()
                    )
                    session = response.data[0]
                    break
                except Exception as inner:
                    last_error = inner
            if attempt == 2:
                raise HTTPException(
                    status_code=500,
                    detail=(
                        f"Failed to create chat session: {exc}. "
                        "Run database/migrations/005_sync_chat_schema.sql "
                        "and 008_lead_gen_3d.sql in Supabase."
                    ),
                ) from exc

    if not session:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create chat session: {last_error}",
        )

    try:
        supabase.table("chat_messages").insert(
            {
                "session_id": session["id"],
                "role": "assistant",
                "message": WELCOME_MESSAGE,
            }
        ).execute()
    except Exception:
        pass

    return {
        "success": True,
        "session": session,
        "welcome_message": WELCOME_MESSAGE,
        "visitor_id": visitor["id"],
        "quota": get_quota(visitor_id=visitor["id"]),
    }


@router.patch("/session/{session_id}")
def update_session(
    session_id: str,
    data: UpdateSessionRequest,
    x_visitor_id: str | None = Header(default=None, alias="X-Visitor-Id"),
):
    title = data.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Title cannot be empty")

    existing = (
        supabase.table("chat_sessions").select("*").eq("id", session_id).execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Session not found")
    if not _session_owned(existing.data[0], x_visitor_id):
        raise HTTPException(status_code=403, detail="Session does not belong to visitor")

    response = (
        supabase.table("chat_sessions")
        .update({"title": title})
        .eq("id", session_id)
        .execute()
    )

    return {
        "success": True,
        "session": response.data[0],
    }


@router.delete("/session/{session_id}")
def delete_session(
    session_id: str,
    x_visitor_id: str | None = Header(default=None, alias="X-Visitor-Id"),
):
    existing = (
        supabase.table("chat_sessions").select("*").eq("id", session_id).execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Session not found")
    if not _session_owned(existing.data[0], x_visitor_id):
        raise HTTPException(status_code=403, detail="Session does not belong to visitor")

    try:
        supabase.table("chat_messages").delete().eq(
            "session_id", session_id
        ).execute()
        supabase.table("booth_requirements").delete().eq(
            "session_id", session_id
        ).execute()
        supabase.table("chat_sessions").delete().eq("id", session_id).execute()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete session: {exc}",
        ) from exc

    return {
        "success": True,
        "deleted_id": session_id,
    }


@router.get("/session/{session_id}")
def get_session(session_id: str):
    response = (
        supabase.table("chat_sessions")
        .select("*")
        .eq("id", session_id)
        .execute()
    )

    if not response.data:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "success": True,
        "session": response.data[0],
        "requirements": get_requirements(session_id),
        "generation_result": get_session_generation_result(session_id),
    }


@router.patch("/session/{session_id}/requirements")
def update_requirements(
    session_id: str,
    data: UpdateRequirementsRequest,
    x_visitor_id: str | None = Header(default=None, alias="X-Visitor-Id"),
):
    existing = (
        supabase.table("chat_sessions").select("*").eq("id", session_id).execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Session not found")
    if not _session_owned(existing.data[0], x_visitor_id):
        raise HTTPException(status_code=403, detail="Session does not belong to visitor")

    current = get_requirements(session_id) or {}
    merged = {**current, **(data.requirements or {})}
    save_requirements(session_id, merged)
    updated = get_requirements(session_id)

    return {
        "success": True,
        "requirements": updated,
        "requirements_complete": is_complete(updated or {}),
    }


@router.get("/session/{session_id}/messages")
def get_messages(session_id: str):
    response = (
        supabase.table("chat_messages")
        .select("*")
        .eq("session_id", session_id)
        .order("created_at")
        .execute()
    )

    return {
        "success": True,
        "messages": response.data,
    }


@router.post("/message")
def send_message(
    data: ChatMessageRequest,
    x_visitor_id: str | None = Header(default=None, alias="X-Visitor-Id"),
):
    visitor = _resolve_visitor(x_visitor_id)
    session_response = (
        supabase.table("chat_sessions")
        .select("*")
        .eq("id", data.session_id)
        .execute()
    )

    if not session_response.data:
        raise HTTPException(status_code=404, detail="Session not found")

    session = session_response.data[0]
    if not _session_owned(session, visitor["id"]):
        raise HTTPException(status_code=403, detail="Session does not belong to visitor")

    supabase.table("chat_messages").insert(
        {
            "session_id": data.session_id,
            "role": "user",
            "message": data.message,
        }
    ).execute()

    agent_result = generate_agent_reply(data.session_id, data.message)
    reply = agent_result["reply"]
    generation_result = None
    quota = get_quota(visitor_id=visitor["id"])

    if agent_result.get("should_generate"):
        try:
            assert_can_generate(visitor_id=visitor["id"])
            generation_result = run_generation_pipeline(data.session_id)
            record_image_attempt(
                session_id=data.session_id,
                visitor_id=visitor["id"],
            )
            quota = get_quota(visitor_id=visitor["id"])
            reply = (
                "Your booth concept has been generated! "
                "You can refine it while free generations remain, "
                "or convert it to 3D after signing up."
            )
        except PermissionError as exc:
            reply = str(exc)
        except Exception as exc:
            error = str(exc).split("|")[0].strip()
            if len(error) > 180:
                error = f"{error[:180]}..."
            reply = (
                f"Image generation failed: {error} "
                "Your requirements are saved — use Regenerate booth image to try again."
            )

    assistant_payload = {
        "session_id": data.session_id,
        "role": "assistant",
        "message": reply,
    }

    if agent_result.get("reasoning_details"):
        assistant_payload["reasoning_details"] = agent_result[
            "reasoning_details"
        ]

    try:
        supabase.table("chat_messages").insert(assistant_payload).execute()
    except Exception:
        assistant_payload.pop("reasoning_details", None)
        supabase.table("chat_messages").insert(assistant_payload).execute()

    return {
        "success": True,
        "reply": reply,
        "requirements": agent_result["requirements"],
        "requirements_complete": agent_result["requirements_complete"],
        "awaiting_confirmation": agent_result.get("awaiting_confirmation", False),
        "missing_fields": agent_result.get("missing_fields", []),
        "generation_result": generation_result,
        "visitor_id": visitor["id"],
        "quota": quota,
    }


@router.post("/session/{session_id}/generate")
def generate_from_session(
    session_id: str,
    x_visitor_id: str | None = Header(default=None, alias="X-Visitor-Id"),
):
    visitor = _resolve_visitor(x_visitor_id)
    session_response = (
        supabase.table("chat_sessions")
        .select("*")
        .eq("id", session_id)
        .execute()
    )

    if not session_response.data:
        raise HTTPException(status_code=404, detail="Session not found")

    session = session_response.data[0]
    if not _session_owned(session, visitor["id"]):
        raise HTTPException(status_code=403, detail="Session does not belong to visitor")

    try:
        assert_can_generate(visitor_id=visitor["id"])
        result = run_generation_pipeline(session_id)
        record_image_attempt(session_id=session_id, visitor_id=visitor["id"])
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {
        "success": True,
        "result": result,
        "visitor_id": visitor["id"],
        "quota": get_quota(visitor_id=visitor["id"]),
    }
