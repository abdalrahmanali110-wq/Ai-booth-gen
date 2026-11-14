"""Unit tests for session ownership and bearer-token auth helpers."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Satisfy supabase client init during import (no live project needed).
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-service-role-key")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


class SessionOwnershipTests(unittest.TestCase):
    def test_matching_visitor_allowed(self):
        from app.services.auth_service import session_belongs_to_visitor

        session = {"visitor_id": "vis-1"}
        self.assertTrue(session_belongs_to_visitor(session, "vis-1"))

    def test_missing_request_visitor_denied(self):
        from app.services.auth_service import session_belongs_to_visitor

        session = {"visitor_id": "vis-1"}
        self.assertFalse(session_belongs_to_visitor(session, None))
        self.assertFalse(session_belongs_to_visitor(session, ""))

    def test_mismatched_visitor_denied(self):
        from app.services.auth_service import session_belongs_to_visitor

        session = {"visitor_id": "vis-1"}
        self.assertFalse(session_belongs_to_visitor(session, "vis-2"))

    def test_unbound_session_not_world_writable(self):
        from app.services.auth_service import session_belongs_to_visitor

        self.assertFalse(session_belongs_to_visitor({}, "vis-1"))
        self.assertFalse(session_belongs_to_visitor({"visitor_id": None}, "vis-1"))


class BearerTokenHelperTests(unittest.TestCase):
    def test_extract_bearer_token(self):
        from app.services.auth_service import extract_bearer_token

        self.assertEqual(extract_bearer_token("Bearer abc.def"), "abc.def")
        self.assertEqual(extract_bearer_token("bearer xyz"), "xyz")
        self.assertIsNone(extract_bearer_token(None))
        self.assertIsNone(extract_bearer_token(""))
        self.assertIsNone(extract_bearer_token("Basic abc"))
        self.assertIsNone(extract_bearer_token("Bearer"))

    def test_require_authenticated_user_missing_header(self):
        from app.services.auth_service import require_authenticated_user

        with self.assertRaises(PermissionError):
            require_authenticated_user(None)

    @patch("app.services.auth_service.httpx.get")
    @patch("app.services.auth_service.SUPABASE_URL", "https://example.supabase.co")
    @patch("app.services.auth_service.SUPABASE_ANON_KEY", "anon-key")
    def test_verify_access_token_success(self, mock_get):
        from app.services.auth_service import verify_access_token

        response = MagicMock()
        response.status_code = 200
        response.content = b'{"id":"user-1","email":"a@b.c"}'
        response.json.return_value = {"id": "user-1", "email": "a@b.c"}
        mock_get.return_value = response

        user = verify_access_token("good-token")
        self.assertEqual(user["id"], "user-1")
        mock_get.assert_called_once()

    @patch("app.services.auth_service.httpx.get")
    @patch("app.services.auth_service.SUPABASE_URL", "https://example.supabase.co")
    @patch("app.services.auth_service.SUPABASE_ANON_KEY", "anon-key")
    def test_verify_access_token_rejects_invalid(self, mock_get):
        from app.services.auth_service import verify_access_token

        response = MagicMock()
        response.status_code = 401
        response.content = b'{"message":"invalid"}'
        response.json.return_value = {"message": "invalid"}
        mock_get.return_value = response

        with self.assertRaises(PermissionError):
            verify_access_token("bad-token")


class ClaimSessionGuardTests(unittest.TestCase):
    @patch("app.services.auth_service.supabase")
    def test_claim_requires_visitor_match(self, mock_supabase):
        from app.services.auth_service import claim_session

        select_chain = MagicMock()
        select_chain.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "sess-1", "visitor_id": "vis-1", "claimed_user_id": None}]
        )
        mock_supabase.table.return_value = select_chain

        with self.assertRaises(PermissionError):
            claim_session(
                session_id="sess-1",
                auth_user_id="user-1",
                visitor_id=None,
            )

        with self.assertRaises(PermissionError):
            claim_session(
                session_id="sess-1",
                auth_user_id="user-1",
                visitor_id="vis-other",
            )

    @patch("app.services.auth_service.supabase")
    def test_claim_rejects_other_users_claim(self, mock_supabase):
        from app.services.auth_service import claim_session

        select_chain = MagicMock()
        select_chain.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[
                {
                    "id": "sess-1",
                    "visitor_id": "vis-1",
                    "claimed_user_id": "user-owner",
                }
            ]
        )
        mock_supabase.table.return_value = select_chain

        with self.assertRaises(PermissionError):
            claim_session(
                session_id="sess-1",
                auth_user_id="user-attacker",
                visitor_id="vis-1",
            )


if __name__ == "__main__":
    unittest.main()
