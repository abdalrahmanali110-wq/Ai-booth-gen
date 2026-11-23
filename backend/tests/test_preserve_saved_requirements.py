"""Regression: chat turns must not wipe summary-popup / PATCH requirement edits."""

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


SAVED_REQUIREMENTS = {
    "brand_name": "Acme Global Labs",
    "industry": "Fashion",
    "event_name": "GITEX",
    "location": "Dubai",
    "booth_size": "6x6",
    "open_sides": "2 sides (corner)",
    "theme": "Premium & Luxury",
    "brand_colors": "black and gold",
    "special_requirements": ["Reception desk", "LED screens"],
    "budget": 70000,
    "slogan": "skip",
    "event_date": "skip",
}

# Chat history still reflects the pre-edit brand from intake.
HISTORY = [
    {
        "role": "assistant",
        "content": "Hello! I am your AI Booth Designer.",
    },
    {
        "role": "user",
        "content": "Design a 6x6 fashion booth for Acme",
    },
    {
        "role": "assistant",
        "content": "Got it — Acme, Fashion, 6x6 booth.",
    },
    {
        "role": "user",
        "content": "GITEX",
    },
    {
        "role": "assistant",
        "content": "What's the event location?",
    },
    {
        "role": "user",
        "content": "Dubai",
    },
]


class PreserveSavedRequirementsTests(unittest.TestCase):
    def test_popup_edits_survive_follow_up_chat_turn(self):
        import app.services.agent_service as agent_service

        saved_calls = []

        def fake_save(session_id, requirements):
            saved_calls.append(dict(requirements))

        with (
            patch.object(
                agent_service,
                "get_conversation_history",
                return_value=list(HISTORY),
            ),
            patch.object(
                agent_service,
                "get_requirements",
                return_value=dict(SAVED_REQUIREMENTS),
            ),
            patch.object(agent_service, "save_requirements", side_effect=fake_save),
            patch.object(agent_service, "maybe_update_session_title"),
            patch.object(
                agent_service,
                "get_llm_provider",
                side_effect=Exception("no llm in unit test"),
            ),
        ):
            result = agent_service.generate_agent_reply(
                "session-1",
                "Can we add more seating?",
            )

        self.assertTrue(saved_calls, "expected requirements to be persisted")
        persisted = saved_calls[-1]
        self.assertEqual(persisted["brand_name"], "Acme Global Labs")
        self.assertEqual(
            persisted["special_requirements"],
            ["Reception desk", "LED screens"],
        )
        self.assertEqual(persisted["budget"], 70000)
        self.assertEqual(result["requirements"]["brand_name"], "Acme Global Labs")

    def test_empty_db_still_extracts_from_history(self):
        import app.services.agent_service as agent_service

        with (
            patch.object(
                agent_service,
                "get_conversation_history",
                return_value=[
                    {"role": "user", "content": "Design a 6x6 fashion booth for Acme"},
                ],
            ),
            patch.object(
                agent_service,
                "get_requirements",
                return_value=agent_service.empty_requirements(),
            ),
            patch.object(agent_service, "save_requirements"),
            patch.object(agent_service, "maybe_update_session_title"),
            patch.object(
                agent_service,
                "get_llm_provider",
                side_effect=Exception("no llm in unit test"),
            ),
        ):
            result = agent_service.generate_agent_reply(
                "session-2",
                "Design a 6x6 fashion booth for Acme",
            )

        reqs = result["requirements"]
        self.assertEqual(reqs["brand_name"], "Acme")
        self.assertEqual(reqs["industry"], "Fashion")
        self.assertEqual(reqs["booth_size"], "6x6")


if __name__ == "__main__":
    unittest.main()
