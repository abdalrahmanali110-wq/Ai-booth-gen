"""Regression: 3D Cloudinary uploads must not overwrite other jobs' assets."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-service-role-key")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("ANON_MAX_IMAGE_GENERATIONS", "3")

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


class CloudinaryPublicIdTests(unittest.TestCase):
    def test_safe_public_id_is_unique_across_calls(self):
        from app.services.model3d_service import _safe_public_id

        first = _safe_public_id("booth-550e8400.glb")
        second = _safe_public_id("booth-550e8400.glb")
        self.assertNotEqual(first, second)
        self.assertTrue(first.startswith("booth-550e8400-"))
        self.assertTrue(second.startswith("booth-550e8400-"))

    def test_upload_model_bytes_never_sets_overwrite_true(self):
        from app.services import model3d_service

        fake_uploader = MagicMock()
        fake_uploader.upload.return_value = {
            "secure_url": "https://res.cloudinary.com/demo/raw/upload/v1/x.glb"
        }

        with patch.dict("sys.modules", {"cloudinary": MagicMock(), "cloudinary.uploader": fake_uploader}):
            # Re-import path uses cloudinary.uploader inside the function.
            with patch("cloudinary.uploader", fake_uploader, create=True):
                url = model3d_service.upload_model_bytes(
                    b"glb-bytes",
                    filename="booth-11111111-2222-3333-4444-555555555555.glb",
                )

        self.assertTrue(url.endswith(".glb") or "cloudinary" in url)
        kwargs = fake_uploader.upload.call_args.kwargs
        self.assertIs(kwargs.get("overwrite"), False)
        public_id = kwargs.get("public_id") or ""
        self.assertIn("booth-11111111-2222-3333-4444-555555555555", public_id)
        # Entropy suffix must be present so two uploads never share a public_id.
        self.assertGreater(len(public_id), len("booth-11111111-2222-3333-4444-555555555555"))

    def test_ephemeral_job_ids_are_unique(self):
        from app.services import model3d_service

        with patch.object(
            model3d_service.supabase.table("model_3d_jobs"),
            "insert",
            side_effect=RuntimeError("table missing"),
        ):
            # supabase.table returns a new builder; patch insert via chain.
            pass

        insert_builder = MagicMock()
        insert_builder.execute.side_effect = RuntimeError("table missing")
        table_builder = MagicMock()
        table_builder.insert.return_value = insert_builder

        with patch.object(model3d_service, "supabase") as supabase:
            supabase.table.return_value = table_builder
            first = model3d_service.create_job(
                user_id="user-a",
                session_id="550e8400-e29b-41d4-a716-446655440000",
                source_image_url="https://cdn.example/a.jpg",
            )
            second = model3d_service.create_job(
                user_id="user-b",
                session_id="55abcdef-0000-4000-8000-000000000001",
                source_image_url="https://cdn.example/b.jpg",
            )

        self.assertTrue(first.get("_ephemeral"))
        self.assertTrue(second.get("_ephemeral"))
        self.assertNotEqual(first["id"], second["id"])
        # Old bug used local-{session[:8]} (then filename[:8] → booth-local-XX,
        # only 256 Cloudinary buckets). New ids keep the full session id plus
        # entropy so process_job filenames cannot collide after truncation.
        self.assertIn("550e8400-e29b-41d4-a716-446655440000", first["id"])
        self.assertIn("55abcdef-0000-4000-8000-000000000001", second["id"])
        self.assertGreater(len(first["id"]), 40)
        self.assertNotEqual(str(first["id"])[:16], str(second["id"])[:16])

    def test_process_job_passes_full_job_id_to_upload(self):
        from app.providers.base import Model3DResult
        from app.services import model3d_service

        job_id = "11111111-2222-3333-4444-555555555555"
        job = {
            "id": job_id,
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
        captured = {}

        def fake_upload(model_bytes, filename="booth.glb"):
            captured["filename"] = filename
            return "https://res.cloudinary.com/demo/raw/upload/v1/unique.glb"

        update_builder = MagicMock()
        update_builder.eq.return_value.execute.return_value = MagicMock(
            data=[{**job, "status": "COMPLETED", "model_url": "https://res.cloudinary.com/demo/raw/upload/v1/unique.glb"}]
        )
        table_builder = MagicMock()
        table_builder.update.return_value = update_builder

        with (
            patch.object(model3d_service, "get_job", return_value=job),
            patch.object(model3d_service, "get_model3d_provider", return_value=provider),
            patch.object(model3d_service, "upload_model_bytes", side_effect=fake_upload),
            patch.object(model3d_service, "supabase") as supabase,
        ):
            supabase.table.return_value = table_builder
            result = model3d_service.process_job(job_id)

        self.assertEqual(captured["filename"], f"booth-{job_id}.glb")
        self.assertNotEqual(captured["filename"], f"booth-{job_id[:8]}.glb")
        self.assertEqual(result.get("status"), "COMPLETED")


if __name__ == "__main__":
    unittest.main()
