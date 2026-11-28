"""Regression: OAuth re-login must not null out saved profile fields."""

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


class UpsertAppUserPreserveTests(unittest.TestCase):
    def test_update_omits_none_phone_and_company(self):
        """Google /auth/oauth/complete typically passes phone=None, company=None."""
        from app.services import auth_service

        existing = {
            "id": "user-1",
            "auth_user_id": "auth-1",
            "email": "old@example.com",
            "full_name": "Ada Lovelace",
            "phone": "+971500000000",
            "company": "Analytical Engines",
            "company_name": "Analytical Engines",
        }
        updated = {
            **existing,
            "email": "ada@example.com",
        }

        table = MagicMock()
        table.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[existing]
        )
        table.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[updated]
        )

        with patch.object(auth_service, "supabase") as supabase:
            supabase.table.return_value = table
            result = auth_service.upsert_app_user(
                auth_user_id="auth-1",
                email="ada@example.com",
                name="Ada Lovelace",
                phone=None,
                company=None,
            )

        self.assertEqual(result["phone"], "+971500000000")
        self.assertEqual(result["company"], "Analytical Engines")

        update_payload = table.update.call_args[0][0]
        self.assertEqual(
            update_payload,
            {
                "auth_user_id": "auth-1",
                "email": "ada@example.com",
                "full_name": "Ada Lovelace",
            },
        )

    def test_update_applies_explicit_phone_and_company(self):
        from app.services import auth_service

        existing = {
            "id": "user-1",
            "auth_user_id": "auth-1",
            "email": "old@example.com",
            "full_name": "Ada",
            "phone": "+971500000000",
            "company": "Old Co",
            "company_name": "Old Co",
        }
        updated = {
            **existing,
            "email": "ada@example.com",
            "phone": "+971511111111",
            "company": "New Co",
            "company_name": "New Co",
        }

        table = MagicMock()
        table.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[existing]
        )
        table.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[updated]
        )

        with patch.object(auth_service, "supabase") as supabase:
            supabase.table.return_value = table
            auth_service.upsert_app_user(
                auth_user_id="auth-1",
                email="ada@example.com",
                name=None,
                phone="+971511111111",
                company="New Co",
            )

        update_payload = table.update.call_args[0][0]
        self.assertEqual(
            update_payload,
            {
                "auth_user_id": "auth-1",
                "email": "ada@example.com",
                "phone": "+971511111111",
                "company": "New Co",
                "company_name": "New Co",
            },
        )

    def test_insert_still_includes_optional_fields(self):
        from app.services import auth_service

        created = {
            "id": "auth-2",
            "auth_user_id": "auth-2",
            "email": "new@example.com",
            "full_name": "Grace",
            "phone": None,
            "company": None,
        }

        table = MagicMock()
        table.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )
        table.insert.return_value.execute.return_value = MagicMock(data=[created])

        with patch.object(auth_service, "supabase") as supabase:
            supabase.table.return_value = table
            result = auth_service.upsert_app_user(
                auth_user_id="auth-2",
                email="new@example.com",
                name="Grace",
                phone=None,
                company=None,
            )

        self.assertEqual(result["email"], "new@example.com")
        insert_payload = table.insert.call_args[0][0]
        self.assertEqual(insert_payload["full_name"], "Grace")
        self.assertIn("phone", insert_payload)
        self.assertIn("company", insert_payload)


if __name__ == "__main__":
    unittest.main()
