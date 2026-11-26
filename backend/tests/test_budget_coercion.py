"""Regression: free-text budgets must not crash generation or chat sanitize."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-service-role-key")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


class BudgetCoercionTests(unittest.TestCase):
    def test_coerce_flexible_and_ranges(self):
        from app.services.gemma_service import coerce_budget_amount

        self.assertEqual(coerce_budget_amount("flexible"), 0)
        self.assertEqual(coerce_budget_amount("TBD"), 0)
        self.assertEqual(coerce_budget_amount("Under 40,000 AED"), 35000)
        self.assertEqual(coerce_budget_amount("40,000–90,000"), 70000)
        self.assertEqual(coerce_budget_amount(70000), 70000)
        self.assertEqual(coerce_budget_amount("70000"), 70000)
        self.assertEqual(coerce_budget_amount(None), 0)

    def test_sanitize_string_budget_does_not_typeerror(self):
        from app.services.gemma_service import _sanitize_requirements

        cleaned = _sanitize_requirements(
            {"budget": "flexible", "booth_size": "6x6"}
        )
        self.assertIsNone(cleaned["budget"])

        ranged = _sanitize_requirements(
            {"budget": "Under 40,000", "booth_size": "6x6"}
        )
        self.assertEqual(ranged["budget"], 35000)

    def test_analyze_budget_accepts_free_text(self):
        from app.services.consultation_report_service import analyze_budget

        report = analyze_budget(
            {
                "budget": "flexible",
                "booth_size": "6x6",
                "theme": "Modern & Tech",
                "special_requirements": ["Reception desk"],
            }
        )
        self.assertEqual(report["user_budget"], 0)
        self.assertIn("sqm", report)

        ranged = analyze_budget(
            {
                "budget": "90,000–180,000 AED",
                "booth_size": "6x6",
                "theme": "Premium & Luxury",
                "special_requirements": [],
            }
        )
        self.assertEqual(ranged["user_budget"], 140000)

    def test_web_search_budget_helper_tolerates_strings(self):
        from app.services.web_search_service import _budget_as_int

        self.assertEqual(_budget_as_int("flexible"), 0)
        self.assertEqual(_budget_as_int("70000"), 70000)
        self.assertEqual(_budget_as_int(None), 0)

    def test_pipeline_returns_image_when_consultation_crashes(self):
        import app.services.agent_service as agent_service

        requirements = {
            "brand_name": "Acme",
            "industry": "Tech",
            "slogan": "skip",
            "event_name": "GITEX",
            "location": "Dubai",
            "event_date": "skip",
            "booth_size": "6x6",
            "open_sides": "2 sides (corner)",
            "theme": "Modern & Tech",
            "brand_colors": "Blue and white",
            "special_requirements": ["LED screens"],
            "budget": "flexible",
        }

        booth_row = {"id": "booth-1"}
        image_row = {
            "id": "img-1",
            "image_url": "https://cdn.example/booth.jpg",
            "booth_request_id": "booth-1",
        }

        table = MagicMock()
        # booth_requests.insert → booth_row
        # generated_images.insert → image_row
        # chat_sessions.update / booth_requirements.update → ok
        insert_results = [MagicMock(data=[booth_row]), MagicMock(data=[image_row])]
        table.insert.return_value.execute.side_effect = insert_results
        table.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{}]
        )

        with (
            patch.object(agent_service, "get_requirements", return_value=requirements),
            patch.object(
                agent_service,
                "generate_booth_image",
                return_value={
                    "image_url": image_row["image_url"],
                    "provider": "test",
                },
            ),
            patch.object(
                agent_service,
                "generate_consultation_report",
                side_effect=ValueError("budget boom"),
            ),
            patch.object(agent_service, "supabase") as supabase,
        ):
            supabase.table.return_value = table
            result = agent_service.run_generation_pipeline("session-1")

        self.assertEqual(result["generated_image"]["image_url"], image_row["image_url"])
        self.assertEqual(result["booth_request"]["id"], "booth-1")
        self.assertIsNotNone(result["budget"])


if __name__ == "__main__":
    unittest.main()
