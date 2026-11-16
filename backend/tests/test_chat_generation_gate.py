"""Regression: chat messages must not auto-start image generation."""

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


COMPLETE_REQUIREMENTS = {
    "brand_name": "Acme",
    "industry": "Fashion",
    "event_name": "Yes Expo Dubai",
    "location": "Dubai",
    "booth_size": "6x6",
    "open_sides": "2",
    "theme": "Modern",
    "brand_colors": "black and gold",
    "special_requirements": [],
    "budget": 50000,
    "slogan": "skip",
    "event_date": "skip",
}


class ChatGenerationGateTests(unittest.TestCase):
    def _run_reply(self, user_message: str):
        import app.services.agent_service as agent_service

        with (
            patch.object(agent_service, "get_conversation_history", return_value=[]),
            patch.object(
                agent_service,
                "extract_requirements_from_conversation",
                return_value=dict(COMPLETE_REQUIREMENTS),
            ),
            patch.object(
                agent_service,
                "contextual_extract_from_turn",
                side_effect=lambda history, message, requirements: requirements,
            ),
            patch.object(
                agent_service,
                "get_llm_provider",
                side_effect=Exception("llm unavailable"),
            ),
            patch.object(agent_service, "save_requirements"),
            patch.object(agent_service, "maybe_update_session_title"),
        ):
            return agent_service.generate_agent_reply("session-1", user_message)

    def test_substring_yes_does_not_autogenerate(self):
        # "yes" appears inside "yesterday" — previously treated as confirmation.
        result = self._run_reply(
            "Actually yesterday we locked the floor plan, keep chatting."
        )
        self.assertTrue(result["requirements_complete"])
        self.assertTrue(result["awaiting_confirmation"])
        self.assertFalse(result["should_generate"])

    def test_dont_generate_yet_does_not_autogenerate(self):
        result = self._run_reply(
            "I don't want to generate yet — need to confirm budget."
        )
        self.assertTrue(result["awaiting_confirmation"])
        self.assertFalse(result["should_generate"])

    def test_explicit_generate_phrase_still_requires_endpoint(self):
        # Even an intentional "generate" chat message must not burn quota;
        # the summary popup hits POST /chat/session/{id}/generate instead.
        result = self._run_reply("generate")
        self.assertTrue(result["awaiting_confirmation"])
        self.assertFalse(result["should_generate"])


if __name__ == "__main__":
    unittest.main()
