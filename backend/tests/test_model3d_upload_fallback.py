"""Regression: production must not COMPLETE 3D jobs with a demo GLB."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-service-role-key")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ["ANON_MAX_IMAGE_GENERATIONS"] = "3"

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


class Model3DUploadFallbackTests(unittest.TestCase):
    def test_upload_failure_marks_failed_in_production(self):
        import app.services.model3d_service as model3d_service
        from app.providers.base import Model3DResult

        job = {
            "id": "11111111-2222-3333-4444-555555555555",
            "source_image_url": "https://cdn.example/booth.jpg",
            "prompt": None,
            "status": "PENDING",
        }
        provider = MagicMock()
        provider.generate_from_image.return_value = Model3DResult(
            model_bytes=b"glb-bytes",
            provider="tripo",
            metadata={},
        )

        with (
            patch.object(model3d_service, "ANON_MAX_IMAGE_GENERATIONS", 3),
            patch.object(model3d_service, "get_job", return_value=job),
            patch.object(model3d_service, "get_model3d_provider", return_value=provider),
            patch.object(
                model3d_service,
                "upload_model_bytes",
                side_effect=RuntimeError("cloudinary down"),
            ),
            patch.object(model3d_service, "supabase") as supabase,
        ):
            # Empty data forces process_job to return the local FAILED payload.
            supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[]
            )
            result = model3d_service.process_job(job["id"], job=job)

        self.assertEqual(result["status"], "FAILED")
        self.assertNotEqual(result.get("model_url"), "/demo-booth.glb")
        self.assertIn("upload failed", (result.get("error") or "").lower())

    def test_upload_failure_may_demo_in_testing_mode(self):
        import app.services.model3d_service as model3d_service
        from app.providers.base import Model3DResult

        job = {
            "id": "11111111-2222-3333-4444-555555555555",
            "source_image_url": "https://cdn.example/booth.jpg",
            "prompt": None,
            "status": "PENDING",
        }
        provider = MagicMock()
        provider.generate_from_image.return_value = Model3DResult(
            model_bytes=b"glb-bytes",
            provider="tripo",
            metadata={},
        )

        with (
            patch.object(model3d_service, "ANON_MAX_IMAGE_GENERATIONS", 0),
            patch.object(model3d_service, "get_job", return_value=job),
            patch.object(model3d_service, "get_model3d_provider", return_value=provider),
            patch.object(
                model3d_service,
                "upload_model_bytes",
                side_effect=RuntimeError("cloudinary down"),
            ),
            patch.object(model3d_service, "supabase") as supabase,
        ):
            supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[
                    {
                        "id": job["id"],
                        "status": "COMPLETED",
                        "model_url": "/demo-booth.glb",
                    }
                ]
            )
            result = model3d_service.process_job(job["id"], job=job)

        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(result["model_url"], "/demo-booth.glb")


if __name__ == "__main__":
    unittest.main()
