from fastapi import APIRouter, Header, HTTPException

from app.models.auth import ClaimSessionRequest, CreateModel3DRequest
from app.services.auth_service import claim_session, create_lead, upsert_app_user
from app.services.model3d_service import (
    create_and_process_job,
    create_job,
    get_job,
    process_job,
)

router = APIRouter()


@router.post("/projects/{session_id}/claim")
def claim_project(
    session_id: str,
    data: ClaimSessionRequest,
    x_visitor_id: str | None = Header(default=None, alias="X-Visitor-Id"),
):
    try:
        if data.email:
            upsert_app_user(
                auth_user_id=data.auth_user_id,
                email=data.email,
                name=data.name,
                phone=data.phone,
                company=data.company,
            )
            create_lead(
                email=data.email,
                name=data.name,
                phone=data.phone,
                company=data.company,
                session_id=session_id,
                auth_user_id=data.auth_user_id,
            )

        session = claim_session(
            session_id=session_id,
            auth_user_id=data.auth_user_id,
            visitor_id=x_visitor_id,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"success": True, "session": session}


@router.post("/projects/{session_id}/models3d")
def enqueue_model3d(
    session_id: str,
    data: CreateModel3DRequest,
    x_visitor_id: str | None = Header(default=None, alias="X-Visitor-Id"),
):
    if not data.auth_user_id:
        raise HTTPException(
            status_code=401,
            detail="Sign in with Google to unlock 3D model generation.",
        )

    try:
        claim_session(
            session_id=session_id,
            auth_user_id=data.auth_user_id,
            visitor_id=x_visitor_id,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception:
        pass

    try:
        if data.process_now:
            job = create_and_process_job(
                user_id=data.auth_user_id,
                session_id=session_id,
                source_image_url=data.source_image_url,
                source_image_id=data.source_image_id,
                prompt=data.prompt,
            )
        else:
            job = create_job(
                user_id=data.auth_user_id,
                session_id=session_id,
                source_image_url=data.source_image_url,
                source_image_id=data.source_image_id,
                prompt=data.prompt,
            )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to create 3D job: {exc}",
        ) from exc

    return {"success": True, "job": job}


@router.get("/models3d/{job_id}")
def get_model3d_job(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="3D job not found")
    return {"success": True, "job": job}


@router.post("/models3d/{job_id}/process")
def process_model3d_job(job_id: str):
    try:
        job = process_job(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"success": True, "job": job}
