from fastapi import APIRouter, Header, HTTPException

from app.models.questionnaire import (
    CreateDesignSessionRequest,
    LeadCaptureRequest,
    SaveAnswersRequest,
)
from app.services import design_service
from app.services.visitor_service import (
    assert_can_generate,
    get_or_create_visitor,
    get_quota,
    record_image_attempt,
)

router = APIRouter()


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


@router.get("/questions")
def get_questions():
    return {
        "success": True,
        **design_service.questions_payload(),
    }


@router.post("/session")
def create_session(
    data: CreateDesignSessionRequest,
    x_visitor_id: str | None = Header(default=None, alias="X-Visitor-Id"),
):
    visitor = _resolve_visitor(x_visitor_id)
    try:
        session = design_service.create_design_session(data.title)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Failed to create design session: {exc}. "
                "Run database/migrations/007_booth_designs.sql in Supabase."
            ),
        ) from exc

    return {
        "success": True,
        "session": session,
        "visitor_id": visitor["id"],
        "quota": get_quota(visitor_id=visitor["id"]),
    }


@router.get("/sessions")
def list_sessions(limit: int = 50):
    # Do not enumerate shared DEFAULT_USER_ID rows — that leaked every visitor's designs.
    sessions = design_service.list_design_sessions(limit=limit)
    return {
        "success": True,
        "sessions": sessions,
    }


@router.get("/session/{session_id}")
def get_session(session_id: str):
    session = design_service.get_design_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "success": True,
        "session": session,
        **design_service.questions_payload(),
    }


@router.patch("/session/{session_id}/answers")
def save_answers(session_id: str, data: SaveAnswersRequest):
    try:
        session = design_service.save_answers(session_id, data.answers)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "success": True,
        "session": session,
    }


@router.post("/session/{session_id}/generate")
def generate(
    session_id: str,
    x_visitor_id: str | None = Header(default=None, alias="X-Visitor-Id"),
):
    visitor = _resolve_visitor(x_visitor_id)
    try:
        assert_can_generate(visitor_id=visitor["id"])
        result = design_service.generate_design(session_id)
        record_image_attempt(session_id=session_id, visitor_id=visitor["id"])
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {
        "success": True,
        "visitor_id": visitor["id"],
        "quota": get_quota(visitor_id=visitor["id"]),
        **result,
    }


@router.post("/session/{session_id}/regenerate")
def regenerate(
    session_id: str,
    x_visitor_id: str | None = Header(default=None, alias="X-Visitor-Id"),
):
    visitor = _resolve_visitor(x_visitor_id)
    try:
        assert_can_generate(visitor_id=visitor["id"])
        result = design_service.regenerate_design(session_id)
        record_image_attempt(session_id=session_id, visitor_id=visitor["id"])
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {
        "success": True,
        "visitor_id": visitor["id"],
        "quota": get_quota(visitor_id=visitor["id"]),
        **result,
    }


@router.post("/session/{session_id}/lead")
def save_lead(session_id: str, data: LeadCaptureRequest):
    try:
        session = design_service.save_lead(
            session_id,
            {
                "name": data.name,
                "email": data.email,
                "phone": data.phone,
            },
        )
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status, detail=message) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "success": True,
        "session": session,
    }
