from fastapi import APIRouter, HTTPException

from app.models.questionnaire import (
    CreateDesignSessionRequest,
    LeadCaptureRequest,
    SaveAnswersRequest,
)
from app.services import design_service

router = APIRouter()


@router.get("/questions")
def get_questions():
    return {
        "success": True,
        **design_service.questions_payload(),
    }


@router.post("/session")
def create_session(data: CreateDesignSessionRequest):
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
    }


@router.get("/sessions")
def list_sessions(limit: int = 50):
    try:
        sessions = design_service.list_design_sessions(limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

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
def generate(session_id: str):
    try:
        result = design_service.generate_design(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {
        "success": True,
        **result,
    }


@router.post("/session/{session_id}/regenerate")
def regenerate(session_id: str):
    try:
        result = design_service.regenerate_design(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {
        "success": True,
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
