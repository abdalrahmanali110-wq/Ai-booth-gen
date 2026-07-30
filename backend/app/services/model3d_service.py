from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.database import supabase
from app.providers.registry import get_model3d_provider


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def upload_model_bytes(model_bytes: bytes, filename: str = "booth.glb") -> str:
    # Cloudinary accepts raw uploads; resource_type auto/raw for glb.
    import cloudinary.uploader

    result = cloudinary.uploader.upload(
        model_bytes,
        folder="ai-booth-generator/models3d",
        resource_type="raw",
        public_id=filename.replace(".glb", ""),
        overwrite=True,
    )
    return result["secure_url"]


def create_job(
    *,
    user_id: str,
    session_id: str,
    source_image_url: str,
    prompt: str | None = None,
    source_image_id: str | None = None,
) -> dict[str, Any]:
    response = (
        supabase.table("model_3d_jobs")
        .insert(
            {
                "user_id": user_id,
                "session_id": session_id,
                "source_image_url": source_image_url,
                "source_image_id": source_image_id,
                "status": "PENDING",
                "prompt": prompt,
            }
        )
        .execute()
    )
    return response.data[0]


def get_job(job_id: str) -> dict[str, Any] | None:
    response = (
        supabase.table("model_3d_jobs").select("*").eq("id", job_id).execute()
    )
    if not response.data:
        return None
    return response.data[0]


def process_job(job_id: str) -> dict[str, Any]:
    job = get_job(job_id)
    if not job:
        raise ValueError("3D job not found")

    if job.get("status") == "COMPLETED" and job.get("model_url"):
        return job

    supabase.table("model_3d_jobs").update(
        {"status": "PROCESSING", "updated_at": _now()}
    ).eq("id", job_id).execute()

    try:
        provider = get_model3d_provider()
        result = provider.generate_from_image(
            job["source_image_url"],
            prompt=job.get("prompt"),
        )
        model_url = upload_model_bytes(
            result.model_bytes,
            filename=f"booth-{job_id[:8]}.glb",
        )
        response = (
            supabase.table("model_3d_jobs")
            .update(
                {
                    "status": "COMPLETED",
                    "provider": result.provider,
                    "model_url": model_url,
                    "error": None,
                    "updated_at": _now(),
                }
            )
            .eq("id", job_id)
            .execute()
        )
        return response.data[0]
    except Exception as exc:
        response = (
            supabase.table("model_3d_jobs")
            .update(
                {
                    "status": "FAILED",
                    "error": str(exc)[:500],
                    "updated_at": _now(),
                }
            )
            .eq("id", job_id)
            .execute()
        )
        return response.data[0]


def create_and_process_job(**kwargs) -> dict[str, Any]:
    job = create_job(**kwargs)
    return process_job(job["id"])
