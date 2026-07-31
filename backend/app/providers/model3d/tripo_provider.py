from __future__ import annotations

import time

import httpx

from app.core.config import TRIPO_API_KEY, TRIPO_MODEL
from app.providers.base import (
    Model3DGenerationProvider,
    Model3DResult,
    ProviderNotConfigured,
)

TRIP_O_BASE = "https://openapi.tripo3d.ai/v3"
POLL_INTERVAL_SEC = 2.0
MAX_POLL_ATTEMPTS = 90  # ~3 minutes


class TripoProvider(Model3DGenerationProvider):
    """Image-to-3D via Tripo OpenAPI (async task + poll + download GLB)."""

    name = "tripo"

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = (api_key or TRIPO_API_KEY or "").strip()
        self.model = (model or TRIPO_MODEL or "v3.1-20260211").strip()

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise ProviderNotConfigured(
                "TRIPO_API_KEY is missing. Add it to backend/.env and Vercel env."
            )
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def generate_from_image(self, image_url: str, *, prompt: str | None = None) -> Model3DResult:
        if not image_url:
            raise ValueError("source image URL is required for Tripo image-to-model")

        headers = self._headers()
        payload: dict = {
            "input": image_url,
            "model": self.model,
            "texture": True,
            "pbr": True,
            "enable_image_autofix": True,
        }
        # prompt is optional metadata for Tripo; keep if API accepts extra fields safely
        if prompt:
            payload["prompt"] = prompt

        with httpx.Client(timeout=120.0) as client:
            create = client.post(
                f"{TRIP_O_BASE}/generation/image-to-model",
                headers=headers,
                json=payload,
            )
            if create.status_code >= 400:
                raise RuntimeError(
                    f"Tripo create failed ({create.status_code}): {create.text[:400]}"
                )

            body = create.json()
            code = body.get("code", 0)
            if code not in (0, "0", None):
                raise RuntimeError(f"Tripo create error: {body}")

            task_id = (body.get("data") or {}).get("task_id")
            if not task_id:
                raise RuntimeError(f"Tripo create missing task_id: {body}")

            task = self._poll_task(client, headers, task_id)
            output = task.get("output") or {}
            model_url = (
                output.get("model_url")
                or output.get("pbr_model_url")
                or output.get("base_model_url")
            )
            if not model_url:
                raise RuntimeError(f"Tripo task succeeded without model_url: {task}")

            download = client.get(model_url, timeout=120.0)
            if download.status_code >= 400:
                raise RuntimeError(
                    f"Tripo model download failed ({download.status_code})"
                )

            return Model3DResult(
                model_bytes=download.content,
                provider=self.name,
                metadata={
                    "source_image": image_url,
                    "task_id": task_id,
                    "tripo_model": self.model,
                    "remote_url": model_url,
                    "rendered_image_url": output.get("rendered_image_url"),
                },
            )

    def _poll_task(
        self,
        client: httpx.Client,
        headers: dict[str, str],
        task_id: str,
    ) -> dict:
        last: dict = {}
        for _ in range(MAX_POLL_ATTEMPTS):
            response = client.get(
                f"{TRIP_O_BASE}/tasks/{task_id}",
                headers=headers,
            )
            if response.status_code >= 400:
                raise RuntimeError(
                    f"Tripo poll failed ({response.status_code}): {response.text[:300]}"
                )
            body = response.json()
            last = body.get("data") or {}
            status = str(last.get("status") or "").lower()
            if status in {"success", "succeeded", "completed"}:
                return last
            if status in {"failed", "error", "cancelled", "canceled"}:
                raise RuntimeError(
                    f"Tripo task {status}: {last.get('error') or last}"
                )
            time.sleep(POLL_INTERVAL_SEC)

        raise TimeoutError(
            f"Tripo task timed out after polling: {task_id} last={last.get('status')}"
        )
