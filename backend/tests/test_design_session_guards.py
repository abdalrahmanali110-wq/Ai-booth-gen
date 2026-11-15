"""Guards for design questionnaire enumeration and generation quota."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-service-role-key")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


class DesignSessionListTests(unittest.TestCase):
    def test_list_design_sessions_never_queries_shared_default_user(self):
        from app.services.design_service import list_design_sessions

        with patch("app.services.design_service.supabase") as mock_supabase:
            sessions = list_design_sessions(limit=50)

        self.assertEqual(sessions, [])
        mock_supabase.table.assert_not_called()


class DesignGenerateQuotaTests(unittest.TestCase):
    def test_generate_enforces_visitor_quota(self):
        from fastapi import HTTPException

        import app.api.questionnaire as questionnaire

        with (
            patch.object(
                questionnaire,
                "get_or_create_visitor",
                return_value={"id": "vis-1"},
            ),
            patch.object(
                questionnaire,
                "assert_can_generate",
                side_effect=PermissionError("Free generation limit reached"),
            ),
            patch.object(questionnaire.design_service, "generate_design") as mock_generate,
            patch.object(questionnaire, "record_image_attempt") as mock_record,
        ):
            with self.assertRaises(HTTPException) as ctx:
                questionnaire.generate("session-1", x_visitor_id="vis-1")

        self.assertEqual(ctx.exception.status_code, 403)
        mock_generate.assert_not_called()
        mock_record.assert_not_called()

    def test_generate_records_attempt_when_allowed(self):
        import app.api.questionnaire as questionnaire

        with (
            patch.object(
                questionnaire,
                "get_or_create_visitor",
                return_value={"id": "vis-1"},
            ),
            patch.object(questionnaire, "assert_can_generate", return_value={"remaining": 2}),
            patch.object(
                questionnaire.design_service,
                "generate_design",
                return_value={
                    "session": {"id": "session-1"},
                    "image_url": "https://example.com/booth.png",
                    "compiled_prompt": "prompt",
                    "provider": "test",
                },
            ),
            patch.object(questionnaire, "record_image_attempt") as mock_record,
            patch.object(
                questionnaire,
                "get_quota",
                return_value={
                    "used": 1,
                    "remaining": 2,
                    "max": 3,
                    "unlimited": False,
                },
            ),
        ):
            result = questionnaire.generate("session-1", x_visitor_id="vis-1")

        self.assertTrue(result["success"])
        self.assertEqual(result["visitor_id"], "vis-1")
        mock_record.assert_called_once_with(session_id="session-1", visitor_id="vis-1")


if __name__ == "__main__":
    unittest.main()
