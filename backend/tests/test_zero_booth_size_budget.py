"""Regression: zero-area booth sizes must not crash analyze_budget."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-service-role-key")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


class ZeroBoothSizeBudgetTests(unittest.TestCase):
    def test_parse_booth_size_rejects_zero_dimensions(self):
        from app.services.consultation_report_service import _parse_booth_size

        self.assertEqual(_parse_booth_size("0x0"), (6, 6, 36))
        self.assertEqual(_parse_booth_size("0x6"), (6, 6, 36))
        self.assertEqual(_parse_booth_size("6x0"), (6, 6, 36))
        self.assertEqual(_parse_booth_size("6x6"), (6, 6, 36))
        self.assertEqual(_parse_booth_size("custom"), (6, 6, 36))

    def test_analyze_budget_survives_zero_area_sizes(self):
        from app.services.consultation_report_service import analyze_budget

        for size in ("0x0", "0x6", "6x0"):
            report = analyze_budget(
                {
                    "budget": 70000,
                    "booth_size": size,
                    "theme": "Modern & Tech",
                    "special_requirements": ["Reception desk"],
                }
            )
            self.assertEqual(report["sqm"], 36, msg=size)
            self.assertEqual(report["user_budget"], 70000)
            self.assertIn("summary", report)


if __name__ == "__main__":
    unittest.main()
