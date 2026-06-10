from fastapi import APIRouter, HTTPException

from app.core.config import DEFAULT_USER_ID
from app.core.database import supabase
from app.models.chat import (
    CreateSessionRequest,
    ChatMessageRequest,
    UpdateSessionRequest,
)
from app.services.agent_service import (
    generate_agent_reply,
    get_requirements,
    get_session_generation_result,
    run_generation_pipeline,
)

router = APIRouter()


WELCOME_MESSAGE = (
    "Hello! I am your AI Exhibition Consultant. "
    "Tell me about your booth — for example: "
    "\"I need a booth for Arab Health.\""
)


@router.post("/session")
def create_session(data: CreateSessionRequest):
    session = None
    last_error = None

    for attempt in range(3):
        try:
            response = (
                supabase.table("chat_sessions")
                .insert(
                    {
                        "user_id": DEFAULT_USER_ID,
                        "title": data.title,
                    }
                )
                .execute()
            )
            session = response.data[0]
            break
        except Exception as exc:
            last_error = exc
            if attempt == 2:
                raise HTTPException(
                    status_code=500,
                    detail=(
                        f"Failed to create chat session: {exc}. "
                        "Run database/migrations/005_sync_chat_schema.sql "
                        "in Supabase."
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
        # Session is still usable; frontend shows welcome from API response.
        pass

    return {
        "success": True,
        "session": session,
        "welcome_message": WELCOME_MESSAGE,
    }


@router.get("/sessions")
def list_sessions(limit: int = 50):
    response = (
        supabase.table("chat_sessions")
        .select("id, title, status, created_at, booth_request_id")
        .eq("user_id", DEFAULT_USER_ID)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    return {
        "success": True,
        "sessions": response.data or [],
    }


@router.patch("/session/{session_id}")
def update_session(session_id: str, data: UpdateSessionRequest):
    title = data.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Title cannot be empty")

    existing = (
        supabase.table("chat_sessions")
        .select("id")
        .eq("id", session_id)
        .eq("user_id", DEFAULT_USER_ID)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Session not found")

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
def delete_session(session_id: str):
    existing = (
        supabase.table("chat_sessions")
        .select("id")
        .eq("id", session_id)
        .eq("user_id", DEFAULT_USER_ID)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Session not found")

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
def send_message(data: ChatMessageRequest):
    session_response = (
        supabase.table("chat_sessions")
        .select("*")
        .eq("id", data.session_id)
        .execute()
    )

    if not session_response.data:
        raise HTTPException(status_code=404, detail="Session not found")

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

    if agent_result["requirements_complete"]:
        try:
            generation_result = run_generation_pipeline(data.session_id)
            reply = (
                "Your booth concept has been generated! "
                "See the analysis below for UAE cost estimates and "
                "recommended exhibition contractors."
            )
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
        "missing_fields": agent_result.get("missing_fields", []),
        "generation_result": generation_result,
    }


@router.post("/session/{session_id}/generate")
def generate_from_session(session_id: str):
    session_response = (
        supabase.table("chat_sessions")
        .select("*")
        .eq("id", session_id)
        .execute()
    )

    if not session_response.data:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        result = run_generation_pipeline(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {
        "success": True,
        "result": result,
    }
