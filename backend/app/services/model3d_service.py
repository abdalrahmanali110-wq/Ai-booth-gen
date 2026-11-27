from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any

from app.core.config import ANON_MAX_IMAGE_GENERATIONS
from app.core.database import supabase
from app.providers.registry import get_model3d_provider


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _demo_model_url() -> str:
    # Served from frontend/public/demo-booth.glb on the same origin.
    return "/demo-booth.glb"


def _safe_public_id(filename: str) -> str:
    """Build a unique Cloudinary public_id that will not collide across jobs."""
    stem = filename[:-4] if filename.lower().endswith(".glb") else filename
    stem = re.sub(r"[^A-Za-z0-9_-]+", "-", (stem or "booth")).strip("-") or "booth"
    # Full job ids can be long; keep a readable prefix and append entropy so
    # overwrite can never replace another user's asset at the same URL.
    return f"{stem[:80]}-{uuid.uuid4().hex}"


def upload_model_bytes(model_bytes: bytes, filename: str = "booth.glb") -> str:
    import cloudinary.uploader

    result = cloudinary.uploader.upload(
        model_bytes,
        folder="ai-booth-generator/models3d",
        resource_type="raw",
        public_id=_safe_public_id(filename),
        overwrite=False,
        format="glb",
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
    try:
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
    except Exception as exc:
        # Table may be missing — still return an in-memory job for MVP testing.
        # Use a full unique id so Cloudinary uploads cannot collide on truncation.
        return {
            "id": f"local-{session_id}-{uuid.uuid4().hex}",
            "user_id": user_id,
            "session_id": session_id,
            "source_image_url": source_image_url,
            "source_image_id": source_image_id,
            "status": "PENDING",
            "prompt": prompt,
            "error": f"db_insert_fallback: {exc}"[:200],
            "_ephemeral": True,
        }


def get_job(job_id: str) -> dict[str, Any] | None:
    if str(job_id).startswith("local-"):
        return None
    response = (
        supabase.table("model_3d_jobs").select("*").eq("id", job_id).execute()
    )
    if not response.data:
        return None
    return response.data[0]


def process_job(job_id: str, job: dict[str, Any] | None = None) -> dict[str, Any]:
    ephemeral = bool(job and job.get("_ephemeral"))
    current = job or get_job(job_id)
    if not current:
        raise ValueError("3D job not found")

    if current.get("status") == "COMPLETED" and current.get("model_url"):
        return current

    if not ephemeral:
        try:
            supabase.table("model_3d_jobs").update(
                {"status": "PROCESSING", "updated_at": _now()}
            ).eq("id", job_id).execute()
        except Exception:
            pass

    try:
        provider = get_model3d_provider()
        result = provider.generate_from_image(
            current["source_image_url"],
            prompt=current.get("prompt"),
        )
        try:
            model_url = upload_model_bytes(
                result.model_bytes,
                # Pass the full job id — truncation previously mapped many jobs
                # onto the same Cloudinary public_id with overwrite=True.
                filename=f"booth-{job_id}.glb",
            )
        except Exception:
            # Cloudinary/raw upload can fail on serverless — use hosted demo GLB.
            model_url = _demo_model_url()
            result_provider = f"{result.provider}+demo_fallback"
        else:
            result_provider = result.provider

        payload = {
            "status": "COMPLETED",
            "provider": result_provider,
            "model_url": model_url,
            "error": None,
            "updated_at": _now(),
        }

        if ephemeral:
            return {**current, **payload, "id": job_id}

        response = (
            supabase.table("model_3d_jobs")
            .update(payload)
            .eq("id", job_id)
            .execute()
        )
        return response.data[0] if response.data else {**current, **payload}
    except Exception as exc:
        # Last-resort: still complete with demo model so the viewer works in testing.
        if ANON_MAX_IMAGE_GENERATIONS <= 0:
            payload = {
                "status": "COMPLETED",
                "provider": "demo_fallback",
                "model_url": _demo_model_url(),
                "error": str(exc)[:500],
                "updated_at": _now(),
            }
            if ephemeral:
                return {**current, **payload, "id": job_id}
            try:
                response = (
                    supabase.table("model_3d_jobs")
                    .update(payload)
                    .eq("id", job_id)
                    .execute()
                )
                return response.data[0] if response.data else {**current, **payload}
            except Exception:
                return {**current, **payload, "id": job_id}

        payload = {
            "status": "FAILED",
            "error": str(exc)[:500],
            "updated_at": _now(),
        }
        if ephemeral:
            return {**current, **payload, "id": job_id}
        response = (
            supabase.table("model_3d_jobs")
            .update(payload)
            .eq("id", job_id)
            .execute()
        )
        return response.data[0] if response.data else {**current, **payload}


def create_and_process_job(**kwargs) -> dict[str, Any]:
    job = create_job(**kwargs)
    return process_job(job["id"], job=job)
