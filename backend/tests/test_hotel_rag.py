"""RAG tests use a temporary SQLite file and mocked, fixed LLM responses."""

import json
from unittest.mock import MagicMock
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from controllers import hotel_rag_controller as rag
from models.database import create_tables


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "hotel_rag_mock_responses.json"
with FIXTURE_PATH.open(encoding="utf-8") as fixture_file:
    MOCKED_OPENROUTER_RESPONSES = json.load(fixture_file)


class TestHotelRag(unittest.TestCase):
    def setUp(self):
        handle = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
        self.db_path = Path(handle.name)
        handle.close()
        connection = sqlite3.connect(self.db_path)
        connection.execute("PRAGMA foreign_keys = ON")
        create_tables(connection)
        connection.executemany(
            "INSERT INTO saved_hotels (hotel_id, name, address, latitude, longitude) VALUES (?, ?, ?, ?, ?)",
            [
                ("hotel-a", "Sample Inn", "1 Main St", 42.0, -71.0),
                ("hotel-b", "Other Hotel", "2 Main St", 42.1, -71.1),
                ("hotel-c", "No Inventory Hotel", "3 Main St", 42.2, -71.2),
            ],
        )
        connection.executemany(
            "INSERT INTO saved_hotel_locations (hotel_id, postcode, locality, country_code, latitude, longitude) VALUES (?, '02108', 'Boston', 'us', 42.0, -71.0)",
            [("hotel-a",), ("hotel-b",), ("hotel-c",)],
        )
        # Hotel A: three included nights at $100; checkout night costs $999 and is excluded.
        nights = [
            ("hotel-a", "2026-10-10", 10000, 2),
            ("hotel-a", "2026-10-11", 10000, 2),
            ("hotel-a", "2026-10-12", 10000, 2),
            ("hotel-a", "2026-10-13", 99900, 20),
            # Hotel B is missing October 11 and must not appear available for all nights.
            ("hotel-b", "2026-10-10", 5000, 1),
            ("hotel-b", "2026-10-12", 5000, 1),
        ]
        connection.executemany(
            "INSERT INTO demo_hotel_nights (hotel_id, stay_date, nightly_rate_cents, rooms_available) VALUES (?, ?, ?, ?)",
            nights,
        )
        connection.commit()
        connection.close()

    def tearDown(self):
        self.db_path.unlink(missing_ok=True)

    def _sql(self, where="l.postcode = '02108'", limit="200"):
        return (
            "SELECT h.hotel_id AS hotel_id, h.name AS name, l.postcode AS postcode, "
            "n.stay_date AS stay_date, n.nightly_rate_cents AS nightly_rate_cents, "
            "n.rooms_available AS rooms_available FROM saved_hotels AS h "
            "JOIN saved_hotel_locations AS l ON l.hotel_id = h.hotel_id "
            "LEFT JOIN demo_hotel_nights AS n ON n.hotel_id = h.hotel_id "
            f"WHERE {where} LIMIT {limit}"
        )

    def _generation(self, sql=None, stay=None, postcode=None):
        proposal = json.loads(json.dumps(MOCKED_OPENROUTER_RESPONSES["sql_proposal"]))
        if sql is not None:
            proposal["sql"] = sql
        if stay is not None:
            proposal["stay"] = stay
        if postcode is not None:
            proposal["postcode"] = postcode
        return json.dumps(proposal)

    def _saved_hotel_state(self):
        connection = sqlite3.connect(self.db_path)
        try:
            return {
                table: connection.execute(
                    f"SELECT * FROM {table} ORDER BY 1, 2"
                ).fetchall()
                for table in (
                    "saved_hotels",
                    "saved_hotel_locations",
                    "demo_hotel_nights",
                )
            }
        finally:
            connection.close()

    def _saved_hotel_count(self):
        connection = sqlite3.connect(self.db_path)
        try:
            return connection.execute("SELECT COUNT(*) FROM saved_hotels").fetchone()[0]
        finally:
            connection.close()

    def test_success_runs_two_mocked_requests_and_grounds_answer(self):
        with patch.object(rag, "_chat_completion", side_effect=[
            self._generation(), MOCKED_OPENROUTER_RESPONSES["grounded_answer"]
        ]) as mock_llm:
            result = rag.ask_saved_hotels("Which hotel is cheapest for October 10–13?", self.db_path)

        self.assertEqual(mock_llm.call_count, 2)
        summary = next(item for item in result["trace"]["derived_stays"] if item["hotel_id"] == "hotel-a")
        self.assertEqual(summary["total_cents"], 30000)
        self.assertTrue(summary["available_for_entire_stay"])
        self.assertNotIn("2026-10-13", summary["included_nights"])
        self.assertEqual(result["answer"], MOCKED_OPENROUTER_RESPONSES["grounded_answer"])
        second_request = mock_llm.call_args_list[1].args[0][1]["content"]
        self.assertIn('"total_cents": 30000', second_request)

    def test_missing_nightly_record_means_incomplete_and_not_available(self):
        with patch.object(rag, "_chat_completion", side_effect=[
            self._generation(), "One saved hotel has incomplete simulated nightly data."
        ]):
            result = rag.ask_saved_hotels("Compare hotel availability for October 10–13", self.db_path)
        summary = next(item for item in result["trace"]["derived_stays"] if item["hotel_id"] == "hotel-b")
        self.assertEqual(summary["missing_dates"], ["2026-10-11"])
        self.assertIsNone(summary["total_cents"])
        self.assertFalse(summary["available_for_entire_stay"])

    def test_hotels_with_no_nights_are_returned_as_incomplete(self):
        rows = rag.execute_readonly_sql(self._sql(), self.db_path)
        summary = next(item for item in rag._derive_stays(
            rows, {"check_in": "2026-10-10", "check_out": "2026-10-13"}
        ) if item["hotel_id"] == "hotel-c")
        self.assertEqual(summary["missing_dates"], ["2026-10-10", "2026-10-11", "2026-10-12"])
        self.assertFalse(summary["available_for_entire_stay"])
        self.assertIsNone(summary["total_cents"])

    def test_checkout_date_is_excluded_from_total(self):
        rows = rag.execute_readonly_sql(self._sql(), self.db_path)
        summary = next(item for item in rag._derive_stays(rows, {"check_in": "2026-10-10", "check_out": "2026-10-13"}) if item["hotel_id"] == "hotel-a")
        self.assertEqual(summary["total_cents"], 30000)
        self.assertNotIn("2026-10-13", [row["stay_date"] for row in summary["nightly_rows"]])

    def test_no_matching_hotels_still_makes_grounded_second_request(self):
        sql = self._sql("l.postcode = '99999'")
        with patch.object(rag, "_chat_completion", side_effect=[
            self._generation(sql=sql, stay=None, postcode="99999"), "No matching saved hotel records were found."
        ]) as mock_llm:
            result = rag.ask_saved_hotels("Which hotels are saved for ZIP 99999?", self.db_path)
        self.assertEqual(mock_llm.call_count, 2)
        self.assertEqual(result["trace"]["retrieved_records"], [])

    def test_rejects_dangerous_or_unbounded_sql_and_database_stays_unchanged(self):
        cases = [
            "DELETE FROM saved_hotels LIMIT 1",
            "INSERT INTO saved_hotels (hotel_id, name, latitude, longitude) VALUES ('bad', 'Bad', 0, 0) LIMIT 1",
            "UPDATE saved_hotels SET name = 'Bad' LIMIT 1",
            "DROP TABLE saved_hotels",
            "ALTER TABLE saved_hotels ADD COLUMN bad TEXT",
            "CREATE TABLE bad (value TEXT)",
            "ATTACH DATABASE 'other.db' AS other",
            self._sql() + "; DELETE FROM saved_hotels",
            self._sql().replace(" LIMIT 200", ""),
            "PRAGMA table_info(saved_hotels) LIMIT 20",
            self._sql().replace("saved_hotels AS h", "sqlite_master AS h"),
            self._sql().replace("n.stay_date AS stay_date", "random() AS stay_date"),
            self._sql(limit="201"),
        ]
        connection = sqlite3.connect(self.db_path)
        tables = ("saved_hotels", "saved_hotel_locations", "demo_hotel_nights")
        before = {
            table: connection.execute(f"SELECT * FROM {table} ORDER BY 1, 2").fetchall()
            for table in tables
        }
        connection.close()
        for query in cases:
            with self.subTest(query=query[:50]):
                with self.assertRaises(rag.SQLRejectedError):
                    rag.execute_readonly_sql(query, self.db_path)
        connection = sqlite3.connect(self.db_path)
        after = {
            table: connection.execute(f"SELECT * FROM {table} ORDER BY 1, 2").fetchall()
            for table in tables
        }
        connection.close()
        self.assertEqual(before, after)

    def test_rejects_fabricated_or_incomplete_read_results(self):
        incomplete = self._sql("l.postcode = '02108' AND n.stay_date = '2026-10-10'")
        fabricated = (
            "SELECT 'invented' AS hotel_id, 'Made Up Hotel' AS name, '02108' AS postcode, "
            "'2026-10-10' AS stay_date, 1 AS nightly_rate_cents, 99 AS rooms_available LIMIT 1"
        )
        for query in (incomplete, fabricated):
            with self.subTest(query=query[:60]):
                with self.assertRaises(rag.SQLRejectedError):
                    rag.execute_readonly_sql(query, self.db_path)

    def test_sql_generation_rejection_never_calls_grounded_answer(self):
        with patch.object(rag, "_chat_completion", return_value=self._generation(
            sql="DELETE FROM saved_hotels LIMIT 1"
        )) as mock_llm:
            with self.assertRaises(rag.SQLRejectedError):
                rag.ask_saved_hotels("Delete a saved hotel", self.db_path)
        self.assertEqual(mock_llm.call_count, 1)

    def test_malicious_llm_proposals_are_rejected_without_database_mutation(self):
        unauthorized_table_query = (
            "SELECT h.hotel_id AS hotel_id, h.hotel_name AS name, h.city AS postcode, "
            "NULL AS stay_date, h.nightly_rate_usd AS nightly_rate_cents, "
            "1 AS rooms_available FROM hotels AS h LIMIT 200"
        )
        rejected_proposals = [
            ("DELETE", "DELETE FROM saved_hotels"),
            ("UPDATE", "UPDATE saved_hotels SET name = 'Compromised'"),
            ("DROP", "DROP TABLE saved_hotels"),
            ("multiple statements", self._sql() + "; DELETE FROM saved_hotels"),
            ("unauthorized table", unauthorized_table_query),
        ]
        observed_counts = []

        for label, sql in rejected_proposals:
            with self.subTest(proposal=label):
                before_count = self._saved_hotel_count()
                before_state = self._saved_hotel_state()
                mocked_proposal = json.dumps({"sql": sql, "stay": None, "postcode": None})
                with patch.object(rag, "_chat_completion", return_value=mocked_proposal) as mock_llm:
                    with self.assertRaises(rag.SQLRejectedError):
                        rag.ask_saved_hotels("Which saved hotels are in my local list?", self.db_path)

                after_count = self._saved_hotel_count()
                after_state = self._saved_hotel_state()
                observed_counts.append((label, before_count, after_count))
                self.assertEqual(mock_llm.call_count, 1, "Rejected SQL must not trigger the answer request")
                self.assertEqual(
                    after_count,
                    before_count,
                    f"saved_hotels count changed for {label}: before={before_count}, after={after_count}",
                )
                self.assertEqual(
                    after_state,
                    before_state,
                    f"saved hotel data changed for {label}: before={before_state}, after={after_state}",
                )

        self.assertEqual(
            observed_counts,
            [(label, 3, 3) for label, _ in rejected_proposals],
        )

    def test_invalid_model_json_and_missing_sql_are_handled(self):
        for bad_response in ("not json", json.dumps({"query": "SELECT 1"})):
            with self.subTest(response=bad_response):
                with patch.object(rag, "_chat_completion", return_value=bad_response):
                    with self.assertRaises(rag.LLMInvalidResponseError):
                        rag.ask_saved_hotels("Which saved hotel is cheapest?", self.db_path)

    def test_invalid_stay_dates_are_rejected(self):
        with patch.object(rag, "_chat_completion", return_value=json.dumps({
            "sql": self._sql(),
            "stay": {"check_in": "2026-10-13", "check_out": "2026-10-10"},
        })):
            with self.assertRaises(rag.LLMInvalidResponseError):
                rag.ask_saved_hotels("Lowest cost for October 10–13", self.db_path)

    def test_rate_limit_provider_failure_and_empty_answer(self):
        with patch.object(rag, "_chat_completion", side_effect=rag.LLMRateLimitError("rate limited")):
            with self.assertRaises(rag.LLMRateLimitError):
                rag.ask_saved_hotels("Which hotel is cheapest?", self.db_path)
        with patch.object(rag, "_chat_completion", side_effect=rag.LLMProviderError("provider down")):
            with self.assertRaises(rag.LLMProviderError):
                rag.ask_saved_hotels("Which hotel is cheapest?", self.db_path)
        first_empty = rag.LLMEmptyResponseError(
            "empty", {"http_status": 200, "finish_reason": "length", "completion_tokens": 1800, "reasoning_tokens": 1800}
        )
        retry_empty = rag.LLMEmptyResponseError(
            "empty", {"http_status": 200, "finish_reason": "length", "completion_tokens": 2400, "reasoning_tokens": 2400}
        )
        with patch.object(rag, "_chat_completion", side_effect=[self._generation(), first_empty, retry_empty]) as mock_llm:
            with self.assertRaises(rag.LLMInvalidResponseError) as error:
                rag.ask_saved_hotels("Which hotel is cheapest?", self.db_path)
        self.assertEqual(mock_llm.call_count, 3)
        self.assertIn("initial_response", error.exception.diagnostic)
        self.assertIn("retry_response", error.exception.diagnostic)
        self.assertIn("finish_reason=length", str(error.exception))

    def test_empty_grounded_answer_retries_once_with_larger_budget(self):
        empty = rag.LLMEmptyResponseError(
            "reasoning-only", {"http_status": 200, "finish_reason": "length", "reasoning_only": True}
        )
        with patch.object(rag, "_chat_completion", side_effect=[
            self._generation(), empty, "A grounded retry answer."
        ]) as mock_llm:
            result = rag.ask_saved_hotels("Which saved hotel is cheapest?", self.db_path)
        self.assertEqual(result["answer"], "A grounded retry answer.")
        self.assertEqual(mock_llm.call_count, 3)
        self.assertEqual(mock_llm.call_args_list[0].kwargs["stage"], "SQL generation")
        self.assertEqual(mock_llm.call_args_list[1].kwargs["max_tokens"], 1800)
        self.assertEqual(mock_llm.call_args_list[1].kwargs["reasoning_effort"], "none")
        self.assertEqual(mock_llm.call_args_list[2].kwargs["max_tokens"], 2400)
        self.assertEqual(mock_llm.call_args_list[2].kwargs["reasoning_effort"], "none")

    def test_empty_sql_generation_retries_once_and_keeps_two_stage_flow(self):
        empty = rag.LLMEmptyResponseError(
            "reasoning-only", {"http_status": 200, "finish_reason": "length", "reasoning_only": True}
        )
        with patch.object(rag, "_chat_completion", side_effect=[
            empty, self._generation(), "Grounded final answer."
        ]) as mock_llm:
            result = rag.ask_saved_hotels("Which saved hotel is cheapest?", self.db_path)
        self.assertEqual(result["answer"], "Grounded final answer.")
        self.assertEqual(mock_llm.call_count, 3)
        self.assertEqual(mock_llm.call_args_list[0].kwargs["stage"], "SQL generation")
        self.assertEqual(mock_llm.call_args_list[1].kwargs["stage"], "SQL generation retry")
        self.assertEqual(mock_llm.call_args_list[1].kwargs["max_tokens"], 2400)
        self.assertEqual(mock_llm.call_args_list[2].kwargs["stage"], "grounded answer")

    def test_empty_response_diagnostics_exclude_reasoning_text(self):
        private_reasoning = "PRIVATE REASONING MUST NEVER LEAK"
        payload = {
            "choices": [{
                "message": {"content": None, "reasoning": private_reasoning, "reasoning_details": [{"type": "reasoning.text"}]},
                "finish_reason": "length",
            }],
            "usage": {
                "prompt_tokens": 263,
                "completion_tokens": 700,
                "total_tokens": 963,
                "completion_tokens_details": {"reasoning_tokens": 700},
            },
        }
        response = MagicMock()
        response.status = 200
        response.__enter__.return_value = response
        response.__exit__.return_value = False
        response.read.return_value = json.dumps(payload).encode("utf-8")
        with patch.object(rag, "get_openrouter_api_key", return_value="test-fixture-only-key"), patch.object(
            rag, "urlopen", return_value=response
        ) as mocked_urlopen:
            with self.assertRaises(rag.LLMEmptyResponseError) as error:
                rag._chat_completion([], max_tokens=700, stage="grounded answer")

        safe_error = str(error.exception)
        for expected in ("HTTP=200", "finish_reason=length", "prompt_tokens=263", "completion_tokens=700", "reasoning_tokens=700", "reasoning_only=True"):
            self.assertIn(expected, safe_error)
        self.assertNotIn(private_reasoning, safe_error)
        self.assertNotIn("test-fixture-only-key", safe_error)
        excluded_reasoning_payload = json.loads(json.dumps(payload))
        excluded_reasoning_payload["choices"][0]["message"] = {"content": None}
        excluded_diagnostic = rag._response_diagnostic(
            excluded_reasoning_payload, 200, "grounded answer"
        )
        self.assertTrue(excluded_diagnostic["reasoning_only"])
        request = mocked_urlopen.call_args.args[0]
        request_body = json.loads(request.data.decode("utf-8"))
        self.assertEqual(request_body["model"], rag.get_openrouter_model())
        self.assertNotIn("models", request_body)
        self.assertEqual(request_body["reasoning"], {"effort": "none", "exclude": True})

    def test_parses_text_blocks_but_never_uses_reasoning_as_answer(self):
        payload = {
            "choices": [{
                "message": {
                    "content": [{"type": "text", "text": "Final user-facing answer."}],
                    "reasoning": "Never return this reasoning.",
                },
                "finish_reason": "stop",
            }],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        }
        response = MagicMock()
        response.status = 200
        response.__enter__.return_value = response
        response.__exit__.return_value = False
        response.read.return_value = json.dumps(payload).encode("utf-8")
        with patch.object(rag, "get_openrouter_api_key", return_value="test-fixture-only-key"), patch.object(
            rag, "urlopen", return_value=response
        ):
            result = rag._chat_completion([], max_tokens=1800)
        self.assertEqual(result, "Final user-facing answer.")
        self.assertNotIn("reasoning", result.lower())

    def test_openrouter_rate_limit_and_network_errors_are_normalized(self):
        secret = "test-fixture-only-key"
        with patch.object(rag, "get_openrouter_api_key", return_value=secret), patch.object(
            rag, "urlopen", side_effect=HTTPError("https://openrouter.ai", 429, "limited", {}, None)
        ):
            with self.assertRaises(rag.LLMRateLimitError) as error:
                rag._chat_completion([], max_tokens=10)
            self.assertNotIn(secret, str(error.exception))

        with patch.object(rag, "get_openrouter_api_key", return_value=secret), patch.object(
            rag, "urlopen", side_effect=URLError("network down")
        ):
            with self.assertRaises(rag.LLMProviderError):
                rag._chat_completion([], max_tokens=10)

    def test_missing_openrouter_key_is_a_configuration_error(self):
        with patch.object(rag, "get_openrouter_api_key", return_value=""):
            with self.assertRaises(rag.RagConfigurationError):
                rag._chat_completion([], max_tokens=10)

    def test_user_supplied_key_is_redacted_from_question_trace(self):
        secret = "sk-or-v1-abcdef0123456789abcdef0123456789"
        with patch.object(rag, "_chat_completion", side_effect=[
            self._generation(), "No matching saved hotel records were found."
        ]) as mock_llm:
            result = rag.ask_saved_hotels(f"Question with {secret}", self.db_path)
        self.assertNotIn(secret, result["trace"]["question"])
        self.assertNotIn(secret, mock_llm.call_args_list[0].args[0][1]["content"])


if __name__ == "__main__":
    unittest.main()
