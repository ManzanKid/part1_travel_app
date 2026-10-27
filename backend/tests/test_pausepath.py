"""PausePath data and recommendation tests use temporary SQLite and mocked LLM output."""

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from controllers import pausepath_controller as controller
from controllers.hotel_rag_controller import (
    LLMInvalidResponseError,
    LLMProviderError,
    LLMRateLimitError,
)
from models.database import create_tables


class TestPausePath(unittest.TestCase):
    def setUp(self):
        handle = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
        self.db_path = Path(handle.name)
        handle.close()
        connection = sqlite3.connect(self.db_path)
        connection.execute("PRAGMA foreign_keys = ON")
        create_tables(connection)
        connection.execute(
            "INSERT INTO hotels VALUES ('H-KEEP', 'Unrelated Hotel', 'Town', 'PA', 90.0)"
        )
        connection.commit()
        connection.close()
        self.valid_session = {
            "skill_id": "breathing",
            "started_at": "2026-10-27T12:00:00.000Z",
            "finished_at": "2026-10-27T12:01:00.000Z",
            "duration_ms": 60_000,
            "status": "completed",
        }

    def tearDown(self):
        self.db_path.unlink(missing_ok=True)

    def _count(self, table):
        connection = sqlite3.connect(self.db_path)
        try:
            return connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        finally:
            connection.close()

    def test_session_is_saved_only_when_create_is_called_and_persists_on_reopen(self):
        self.assertEqual(self._count("pausepath_sessions"), 0)

        created = controller.create_session(self.valid_session, self.db_path)

        self.assertTrue(created["session_id"])
        self.assertEqual(created["skill_id"], "breathing")
        self.assertEqual(created["duration_ms"], 60_000)
        # get_history opens a fresh connection, matching a backend process reopening SQLite.
        history = controller.get_history(self.db_path)
        self.assertEqual(len(history["sessions"]), 1)
        self.assertEqual(history["sessions"][0]["session_id"], created["session_id"])
        self.assertEqual(history["last_skill_id"], "breathing")
        self.assertEqual(history["conversations"], [])
        stopped_payload = {
            **self.valid_session,
            "skill_id": "stop",
            "finished_at": "2026-10-27T12:02:00.000Z",
            "duration_ms": 5_000,
            "status": "stopped",
        }
        controller.create_session(stopped_payload, self.db_path)
        reopened_history = controller.get_history(self.db_path)
        self.assertEqual(reopened_history["sessions"][0]["status"], "stopped")
        self.assertEqual(reopened_history["last_skill_id"], "stop")

    def test_session_delete_preserves_unrelated_hotel_data(self):
        created = controller.create_session(self.valid_session, self.db_path)
        controller.delete_session(created["session_id"], self.db_path)
        self.assertEqual(controller.get_history(self.db_path)["sessions"], [])
        connection = sqlite3.connect(self.db_path)
        try:
            self.assertEqual(
                connection.execute("SELECT hotel_name FROM hotels WHERE hotel_id='H-KEEP'").fetchone()[0],
                "Unrelated Hotel",
            )
        finally:
            connection.close()

    def test_session_validation_enforces_skill_status_time_and_duration(self):
        invalid_payloads = [
            {**self.valid_session, "skill_id": "therapy"},
            {**self.valid_session, "status": "paused"},
            {**self.valid_session, "started_at": "2026-10-27 12:00:00"},
            {**self.valid_session, "finished_at": "2026-10-27T11:59:00.000Z"},
            {**self.valid_session, "duration_ms": -1},
            {**self.valid_session, "duration_ms": 3_600_001},
        ]
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    controller.create_session(payload, self.db_path)
        self.assertEqual(self._count("pausepath_sessions"), 0)

    def test_fixed_exercise_rules_and_skill_ids(self):
        self.assertEqual(controller.ALLOWED_SKILL_IDS, {"breathing", "stop"})
        breathing_seconds = sum(controller.BREATHING_PHASE_SECONDS) * controller.BREATHING_CYCLES
        stop_seconds = len(controller.STOP_INSTRUCTIONS) * controller.STOP_STEP_SECONDS
        self.assertEqual(controller.BREATHING_PHASE_SECONDS, (4, 6))
        self.assertEqual(breathing_seconds, 60)
        self.assertEqual(controller.STOP_INSTRUCTIONS, (
            "Stop.",
            "Take a step back.",
            "Observe what is happening internally and externally.",
            "Proceed mindfully.",
        ))
        self.assertEqual(stop_seconds, 60)
        self.assertLess(breathing_seconds, 90)
        self.assertLess(stop_seconds, 90)

    def test_fictional_conversation_requires_explicit_save_and_persists(self):
        self.assertEqual(controller.get_history(self.db_path)["conversations"], [])
        saved = controller.save_conversation(
            "A fictional student feels rushed before a presentation.", "stop", self.db_path
        )
        history = controller.get_history(self.db_path)
        self.assertEqual(len(history["conversations"]), 1)
        conversation = history["conversations"][0]
        self.assertEqual(conversation["thread_id"], saved["thread_id"])
        self.assertEqual([message["role"] for message in conversation["messages"]], ["user", "assistant"])
        self.assertIn("fictional student", conversation["messages"][0]["content"])
        self.assertIn("optional", conversation["messages"][1]["content"].lower())

    def test_conversation_validation_and_cascade_delete(self):
        with self.assertRaises(ValueError):
            controller.save_conversation("A scenario", "unapproved", self.db_path)
        with self.assertRaises(ValueError):
            controller.save_conversation("x" * 161, "stop", self.db_path)
        saved = controller.save_conversation("A fictional scene.", "breathing", self.db_path)
        controller.delete_conversation(saved["thread_id"], self.db_path)
        self.assertEqual(controller.get_history(self.db_path)["conversations"], [])
        self.assertEqual(self._count("pausepath_chat_messages"), 0)

    def test_crisis_phrases_bypass_model_and_are_not_saved_as_conversations(self):
        self.assertTrue(controller.contains_obvious_crisis_language(
            "A fictional person wants to die."
        ))
        with patch.object(controller, "_chat_completion") as mock_llm:
            result = controller.recommend_skill("A fictional character wants to end my life")
        self.assertEqual(result, {"crisis_info": True})
        mock_llm.assert_not_called()
        with self.assertRaises(ValueError):
            controller.save_conversation("A fictional character wants to end my life", "stop", self.db_path)
        self.assertEqual(controller.get_history(self.db_path)["conversations"], [])

    def test_valid_model_suggestion_returns_only_an_allowlisted_skill(self):
        with patch.object(controller, "get_openrouter_model", return_value="nvidia/nemotron-3.5-lightning:free"), patch.object(
            controller, "_chat_completion", return_value=json.dumps({"skill_id": "stop"})
        ) as mock_llm:
            result = controller.recommend_skill("A fictional student feels rushed.")
        self.assertEqual(result, {"skill_id": "stop"})
        mock_llm.assert_called_once()
        self.assertEqual(mock_llm.call_args.kwargs["max_tokens"], 120)
        self.assertEqual(mock_llm.call_args.kwargs["stage"], "PausePath recommendation")
        self.assertIn("exactly one JSON object", mock_llm.call_args.args[0][0]["content"])

    def test_invalid_model_suggestions_fail_safely(self):
        invalid_outputs = (
            "not JSON",
            json.dumps({"skill_id": "therapy"}),
            json.dumps({"skill_id": ["stop"]}),
            json.dumps({"skill_id": "stop", "instructions": "Try a new exercise."}),
        )
        for output in invalid_outputs:
            with self.subTest(output=output):
                with patch.object(controller, "get_openrouter_model", return_value="nvidia/nemotron-3.5-lightning:free"), patch.object(
                    controller, "_chat_completion", return_value=output
                ):
                    with self.assertRaises(controller.PausePathRecommendationError):
                        controller.recommend_skill("A fictional student feels rushed.")

    def test_model_provider_and_rate_limit_failures_leave_direct_choices_available(self):
        for error in (
            LLMProviderError("provider unavailable"),
            LLMRateLimitError("rate limited"),
            LLMInvalidResponseError("invalid output"),
        ):
            with self.subTest(error=type(error).__name__):
                with patch.object(controller, "get_openrouter_model", return_value="nvidia/nemotron-3.5-lightning:free"), patch.object(
                    controller, "_chat_completion", side_effect=error
                ):
                    with self.assertRaises(controller.PausePathRecommendationError) as raised:
                        controller.recommend_skill("A fictional student feels rushed.")
                self.assertIn("choose either activity", str(raised.exception))

    def test_paid_model_configuration_is_rejected_without_a_request(self):
        with patch.object(controller, "get_openrouter_model", return_value="example/paid-model"), patch.object(
            controller, "_chat_completion"
        ) as mock_llm:
            with self.assertRaises(controller.PausePathRecommendationError):
                controller.recommend_skill("A fictional student feels rushed.")
        mock_llm.assert_not_called()

    def test_simpler_view_preference_persists_and_history_can_be_cleared(self):
        self.assertFalse(controller.get_preferences(self.db_path)["simpler_view"])
        self.assertEqual(controller.set_simpler_view(True, self.db_path), {"simpler_view": True})
        self.assertTrue(controller.get_preferences(self.db_path)["simpler_view"])
        controller.create_session(self.valid_session, self.db_path)
        controller.save_conversation("A fictional scene.", "stop", self.db_path)
        controller.delete_all_history(self.db_path)
        self.assertEqual(controller.get_history(self.db_path)["sessions"], [])
        self.assertEqual(controller.get_history(self.db_path)["conversations"], [])
        self.assertTrue(controller.get_preferences(self.db_path)["simpler_view"])


if __name__ == "__main__":
    unittest.main()
