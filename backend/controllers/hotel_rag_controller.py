"""SQL-grounded answers about locally saved hotels."""

import json
import re
import sqlite3
import time
from datetime import date, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from config import get_openrouter_api_key, get_openrouter_model
from models.database import DB_PATH


MAX_QUESTION_LENGTH = 500
MAX_SQL_LENGTH = 4000
MAX_SQL_ROWS = 200
MAX_TRACE_ROWS = MAX_SQL_ROWS
MAX_STAY_NIGHTS = 31
QUERY_TIMEOUT_SECONDS = 1.5

HOTEL_TABLES = {
    "saved_hotels": {"hotel_id", "name", "address", "latitude", "longitude"},
    "saved_hotel_locations": {
        "hotel_id", "postcode", "locality", "country_code", "latitude", "longitude"
    },
    "demo_hotel_nights": {
        "hotel_id", "stay_date", "nightly_rate_cents", "rooms_available"
    },
}

RAW_RESULT_COLUMNS = (
    "hotel_id", "name", "postcode", "stay_date",
    "nightly_rate_cents", "rooms_available",
)

SCHEMA_DESCRIPTION = """
Allowlisted tables:
saved_hotels(hotel_id TEXT PRIMARY KEY, name TEXT, address TEXT,
             latitude REAL, longitude REAL)
saved_hotel_locations(hotel_id TEXT, postcode TEXT, locality TEXT,
                      country_code TEXT, latitude REAL, longitude REAL,
                      PRIMARY KEY(hotel_id, postcode))
demo_hotel_nights(hotel_id TEXT, stay_date TEXT ISO YYYY-MM-DD,
                  nightly_rate_cents INTEGER, rooms_available INTEGER,
                  PRIMARY KEY(hotel_id, stay_date))
Relations: saved_hotels.hotel_id = saved_hotel_locations.hotel_id =
demo_hotel_nights.hotel_id. Keep each result at nightly-row granularity.
""".strip()


class RagError(Exception):
    """Base class for safe, user-displayable chatbot errors."""


class LLMInvalidResponseError(RagError):
    def __init__(self, message, diagnostic=None):
        self.diagnostic = diagnostic or {}
        super().__init__(message)


class LLMEmptyResponseError(LLMInvalidResponseError):
    pass


class RagConfigurationError(RagError):
    pass


class LLMProviderError(RagError):
    def __init__(self, message, diagnostic=None):
        self.diagnostic = diagnostic or {}
        super().__init__(message)


class LLMRateLimitError(LLMProviderError):
    pass


class SQLRejectedError(RagError):
    pass


def _safe_question(question):
    """Validate question size and redact any supplied OpenRouter credential."""
    if not isinstance(question, str) or not question.strip():
        raise ValueError("Enter a question about your saved hotels.")
    if len(question) > MAX_QUESTION_LENGTH:
        raise ValueError(f"Keep questions under {MAX_QUESTION_LENGTH} characters.")
    sanitized = question.strip()
    configured_key = get_openrouter_api_key()
    if configured_key:
        sanitized = sanitized.replace(configured_key, "[redacted credential]")
    sanitized = re.sub(r"sk-or-v1-[A-Za-z0-9_-]{12,}", "[redacted credential]", sanitized)
    sanitized = re.sub(
        r"(?i)(OPENROUTER_API_KEY\s*=\s*)\S+",
        r"\1[redacted credential]",
        sanitized,
    )
    return sanitized


def _token_count(value):
    return value if isinstance(value, int) and value >= 0 else None


def _response_diagnostic(payload, http_status, stage):
    """Extract safe response metadata only; never copy answer or reasoning text."""
    choices = payload.get("choices") if isinstance(payload, dict) else None
    choice = choices[0] if isinstance(choices, list) and choices else {}
    if not isinstance(choice, dict):
        choice = {}
    message = choice.get("message")
    if not isinstance(message, dict):
        message = {}
    usage = payload.get("usage") if isinstance(payload, dict) else {}
    usage = usage if isinstance(usage, dict) else {}
    completion_details = usage.get("completion_tokens_details") or usage.get("completionTokensDetails") or {}
    completion_details = completion_details if isinstance(completion_details, dict) else {}
    content = message.get("content")
    reasoning = message.get("reasoning") or message.get("reasoning_content")
    reasoning_details = message.get("reasoning_details")
    tool_calls = message.get("tool_calls")
    completion_tokens = _token_count(usage.get("completion_tokens", usage.get("output_tokens")))
    reasoning_tokens = _token_count(
        completion_details.get("reasoning_tokens", completion_details.get("reasoningTokens"))
    )
    reasoning_only = not bool(content) and (
        bool(reasoning or reasoning_details)
        or (
            completion_tokens is not None
            and reasoning_tokens is not None
            and reasoning_tokens > 0
            and reasoning_tokens >= completion_tokens
        )
    )
    return {
        "stage": stage,
        "http_status": http_status,
        "finish_reason": choice.get("finish_reason"),
        "prompt_tokens": _token_count(usage.get("prompt_tokens", usage.get("input_tokens"))),
        "completion_tokens": completion_tokens,
        "total_tokens": _token_count(usage.get("total_tokens")),
        "reasoning_tokens": reasoning_tokens,
        "response_format": "chat_completion" if isinstance(choices, list) else "unexpected",
        "content_type": type(content).__name__ if content is not None else "null",
        "content_characters": len(content) if isinstance(content, str) else None,
        "reasoning_only": reasoning_only,
        "reasoning_characters": len(reasoning) if isinstance(reasoning, str) else None,
        "reasoning_detail_count": len(reasoning_details) if isinstance(reasoning_details, list) else None,
        "tool_call_count": len(tool_calls) if isinstance(tool_calls, list) else 0,
    }


def _diagnostic_summary(diagnostic):
    """Render only status, finish, token counts, and safe shape metadata."""
    labels = (
        ("stage", "stage"),
        ("http_status", "HTTP"),
        ("finish_reason", "finish_reason"),
        ("prompt_tokens", "prompt_tokens"),
        ("completion_tokens", "completion_tokens"),
        ("reasoning_tokens", "reasoning_tokens"),
        ("total_tokens", "total_tokens"),
        ("response_format", "response_format"),
        ("content_type", "content_type"),
        ("content_characters", "content_characters"),
        ("reasoning_only", "reasoning_only"),
    )
    details = [f"{label}={diagnostic[key]}" for key, label in labels if diagnostic.get(key) is not None]
    return "; ".join(details)


def _content_text(content):
    """Extract user-facing text only; never use message.reasoning as answer content."""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        text_parts = [
            block.get("text", "")
            for block in content
            if isinstance(block, dict)
            and block.get("type") in ("text", "output_text")
            and isinstance(block.get("text"), str)
        ]
        return "\n".join(part.strip() for part in text_parts if part.strip())
    return ""


def _chat_completion(messages, max_tokens, stage="LLM request", reasoning_effort="none"):
    """Make one backend-only OpenRouter request without logging credentials."""
    api_key = get_openrouter_api_key()
    if not api_key:
        raise RagConfigurationError("The chatbot is not configured yet. Add OPENROUTER_API_KEY to the project .env file.")

    request_data = json.dumps({
        "model": get_openrouter_model(),
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": max_tokens,
        "reasoning": {"effort": reasoning_effort, "exclude": True},
    }).encode("utf-8")
    request = Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=request_data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:5173",
            "X-Title": "Expedia Lite",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            http_status = getattr(response, "status", None) or response.getcode()
            payload = json.load(response)
    except HTTPError as error:
        diagnostic = {"stage": stage, "http_status": error.code, "upstream_error": True}
        if error.code == 429:
            raise LLMRateLimitError(
                f"The model is busy or rate-limited (HTTP {error.code}; stage={stage}). Please try again shortly.",
                diagnostic,
            ) from None
        if error.code in (401, 403):
            raise RagConfigurationError(
                f"OpenRouter rejected the configured API key (HTTP {error.code}; stage={stage})."
            ) from None
        raise LLMProviderError(
            f"The answer service could not complete the request (HTTP {error.code}; stage={stage}).",
            diagnostic,
        ) from None
    except (URLError, TimeoutError, OSError) as error:
        diagnostic = {"stage": stage, "transport_error": type(error).__name__}
        raise LLMProviderError(
            f"The answer service is unavailable ({type(error).__name__}; stage={stage}). Please try again.",
            diagnostic,
        ) from None
    except ValueError:
        diagnostic = {"stage": stage, "http_status": locals().get("http_status"), "response_format": "invalid_json"}
        raise LLMInvalidResponseError(
            "The answer service returned invalid JSON (" + _diagnostic_summary(diagnostic) + ").",
            diagnostic,
        ) from None

    diagnostic = _response_diagnostic(payload, http_status, stage)
    choices = payload.get("choices") if isinstance(payload, dict) else None
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise LLMInvalidResponseError(
            "The answer service returned an unexpected response format (" + _diagnostic_summary(diagnostic) + ").",
            diagnostic,
        )
    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise LLMInvalidResponseError(
            "The answer service returned no chat-completion message (" + _diagnostic_summary(diagnostic) + ").",
            diagnostic,
        )
    raw_content = message.get("content")
    content = _content_text(raw_content)
    if not content or choices[0].get("finish_reason") == "length":
        if diagnostic["reasoning_only"]:
            kind = "reasoning-only response"
        elif not isinstance(raw_content, (str, list)):
            kind = "unexpected content format"
        elif choices[0].get("finish_reason") == "length":
            kind = "token-limited response"
        else:
            kind = "empty response"
        raise LLMEmptyResponseError(
            f"The answer service returned no complete user-facing text ({kind}; {_diagnostic_summary(diagnostic)}).",
            diagnostic,
        )
    return content


def _parse_generation(content):
    """Parse one strict JSON object containing SQL and optional stay dates."""
    try:
        data = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        raise LLMInvalidResponseError("The model did not return valid JSON for the SQL proposal.") from None
    if not isinstance(data, dict) or not isinstance(data.get("sql"), str):
        raise LLMInvalidResponseError("The model response must contain a SQL string.")
    stay = data.get("stay")
    if stay is not None:
        if not isinstance(stay, dict):
            raise LLMInvalidResponseError("The model returned invalid stay dates.")
        try:
            check_in = date.fromisoformat(stay["check_in"])
            check_out = date.fromisoformat(stay["check_out"])
        except (KeyError, TypeError, ValueError):
            raise LLMInvalidResponseError("The model returned invalid stay dates.") from None
        nights = (check_out - check_in).days
        if nights < 1 or nights > MAX_STAY_NIGHTS:
            raise LLMInvalidResponseError("The requested stay must be between 1 and 31 nights.")
        stay = {"check_in": check_in.isoformat(), "check_out": check_out.isoformat()}
    postcode = data.get("postcode")
    if postcode is not None and (
        not isinstance(postcode, str) or len(postcode) != 5 or not postcode.isdigit()
    ):
        raise LLMInvalidResponseError("The model returned an invalid ZIP filter.")
    return data["sql"], stay, postcode


def _top_level_tokens(sql):
    """Lex SQL enough to locate top-level keywords without parsing quoted text as code."""
    tokens = []
    depth = 0
    index = 0
    while index < len(sql):
        char = sql[index]
        if char.isspace():
            index += 1
            continue
        if sql.startswith("--", index) or sql.startswith("/*", index):
            raise SQLRejectedError("SQL comments are not accepted in chatbot queries.")
        if char == "'":
            index += 1
            while index < len(sql):
                if sql[index] == "'":
                    if index + 1 < len(sql) and sql[index + 1] == "'":
                        index += 2
                        continue
                    index += 1
                    break
                index += 1
            else:
                raise SQLRejectedError("The SQL contains an unclosed string.")
            tokens.append(("<STRING>", depth))
            continue
        if char in ('"', '`', '['):
            closer = ']' if char == '[' else char
            index += 1
            while index < len(sql):
                if sql[index] == closer:
                    if closer != ']' and index + 1 < len(sql) and sql[index + 1] == closer:
                        index += 2
                        continue
                    index += 1
                    break
                index += 1
            else:
                raise SQLRejectedError("The SQL contains an unclosed identifier.")
            tokens.append(("<IDENTIFIER>", depth))
            continue
        if char == "(":
            tokens.append((char, depth))
            depth += 1
            index += 1
            continue
        if char == ")":
            depth -= 1
            if depth < 0:
                raise SQLRejectedError("The SQL parentheses are unbalanced.")
            tokens.append((char, depth))
            index += 1
            continue
        if char == ";":
            tokens.append((char, depth))
            index += 1
            continue
        if char.isalnum() or char == "_":
            start = index
            while index < len(sql) and (sql[index].isalnum() or sql[index] == "_"):
                index += 1
            tokens.append((sql[start:index], depth))
            continue
        tokens.append((char, depth))
        index += 1
    if depth != 0:
        raise SQLRejectedError("The SQL parentheses are unbalanced.")
    return tokens


def _validate_sql_shape(sql):
    if not isinstance(sql, str) or not sql.strip() or len(sql) > MAX_SQL_LENGTH:
        raise SQLRejectedError("The proposed SQL is empty or too long.")
    tokens = _top_level_tokens(sql)
    top_words = [value.upper() for value, depth in tokens if depth == 0]
    if not top_words or top_words[0] not in ("SELECT", "WITH"):
        raise SQLRejectedError("Only a SELECT query is allowed.")
    if sum(value == ";" for value, _ in tokens) > 1:
        raise SQLRejectedError("Multiple SQL statements are not allowed.")
    if ";" in [value for value, _ in tokens[:-1]]:
        raise SQLRejectedError("Only one SQL statement is allowed.")
    limits = [index for index, (value, depth) in enumerate(tokens) if depth == 0 and value.upper() == "LIMIT"]
    if len(limits) != 1:
        raise SQLRejectedError("The SQL must include one bounded LIMIT clause.")
    limit_index = limits[0]
    if limit_index + 1 >= len(tokens):
        raise SQLRejectedError("The SQL LIMIT value is missing.")
    limit_token = tokens[limit_index + 1][0]
    if not limit_token.isdigit() or int(limit_token) < 1 or int(limit_token) > MAX_SQL_ROWS:
        raise SQLRejectedError(f"The SQL LIMIT must be an integer from 1 to {MAX_SQL_ROWS}.")
    tail = [value for value, depth in tokens[limit_index + 2:] if depth == 0]
    if any(value != ";" for value in tail):
        raise SQLRejectedError("The LIMIT clause must end the query.")


def _authorizer(action, arg1, arg2, database_name, trigger_name):
    if action == sqlite3.SQLITE_SELECT:
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_READ:
        allowed_columns = HOTEL_TABLES.get(arg1 or "")
        if allowed_columns is not None and arg2 in allowed_columns:
            return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY
    if action == sqlite3.SQLITE_FUNCTION:
        # The retrieval contract needs raw rows, not aggregate or arbitrary functions.
        return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_DENY


def _canonical_records(connection, postcode=None, stay=None):
    """Build an expected complete result set using fixed, parameterized local SQL."""
    join = "LEFT JOIN demo_hotel_nights AS n ON n.hotel_id = h.hotel_id"
    params = []
    if stay is not None:
        join += " AND n.stay_date >= ? AND n.stay_date < ?"
        params.extend((stay["check_in"], stay["check_out"]))
    where = ""
    if postcode is not None:
        where = "WHERE l.postcode = ?"
        params.append(postcode)
    canonical_sql = (
        "SELECT h.hotel_id AS hotel_id, h.name AS name, l.postcode AS postcode, "
        "n.stay_date AS stay_date, n.nightly_rate_cents AS nightly_rate_cents, "
        "n.rooms_available AS rooms_available FROM saved_hotels AS h "
        "JOIN saved_hotel_locations AS l ON l.hotel_id = h.hotel_id "
        f"{join} {where} ORDER BY h.hotel_id, l.postcode, n.stay_date LIMIT 201"
    )
    connection.set_authorizer(_authorizer)
    rows = [dict(row) for row in connection.execute(canonical_sql, params).fetchmany(201)]
    if len(rows) > MAX_SQL_ROWS:
        raise SQLRejectedError("The matching saved hotel data exceeds the bounded result limit.")
    return rows


def _record_key(record):
    return tuple(record[column] for column in RAW_RESULT_COLUMNS)


def execute_readonly_sql(sql, db_path=None, postcode=None, stay=None):
    """Validate, authorize, and execute one bounded SELECT on a read-only DB handle."""
    _validate_sql_shape(sql)
    path = Path(db_path or DB_PATH).resolve()
    if not path.is_file():
        raise SQLRejectedError("The saved hotel database is not available.")
    uri = path.as_uri() + "?mode=ro"
    try:
        connection = sqlite3.connect(uri, uri=True)
    except sqlite3.Error:
        raise SQLRejectedError("Could not open the saved hotel database read-only.") from None
    started = time.monotonic()
    try:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only = ON")
        connection.set_authorizer(_authorizer)
        connection.set_progress_handler(
            lambda: 1 if time.monotonic() - started > QUERY_TIMEOUT_SECONDS else 0,
            1000,
        )
        cursor = connection.execute(sql)
        column_names = tuple(item[0] for item in (cursor.description or ()))
        if column_names != RAW_RESULT_COLUMNS:
            raise SQLRejectedError("The SQL must return the six raw saved-hotel nightly columns in the documented order.")
        rows = [dict(row) for row in cursor.fetchmany(MAX_SQL_ROWS + 1)]
        if len(rows) > MAX_SQL_ROWS:
            raise SQLRejectedError("The SQL returned more than the allowed row limit.")
        expected = _canonical_records(connection, postcode, stay)
        if sorted(map(_record_key, rows), key=repr) != sorted(map(_record_key, expected), key=repr):
            raise SQLRejectedError("The SQL result was incomplete or did not match saved hotel records.")
        return rows
    except SQLRejectedError:
        raise
    except sqlite3.Error:
        raise SQLRejectedError("The proposed SQL was rejected by SQLite's read-only authorization checks.") from None
    finally:
        connection.close()


def _derive_stays(rows, stay):
    if stay is None:
        return []
    first = date.fromisoformat(stay["check_in"])
    last = date.fromisoformat(stay["check_out"])
    expected_dates = [(first + timedelta(days=offset)).isoformat() for offset in range((last - first).days)]
    by_hotel = {}
    for row in rows:
        key = (row["hotel_id"], row["postcode"])
        hotel = by_hotel.setdefault(key, {
            "hotel_id": row["hotel_id"], "name": row["name"], "postcode": row["postcode"], "night_map": {}
        })
        if row["stay_date"] in expected_dates:
            hotel["night_map"][row["stay_date"]] = row

    summaries = []
    for hotel in by_hotel.values():
        missing = [night for night in expected_dates if night not in hotel["night_map"]]
        total_cents = None if missing else sum(
            int(hotel["night_map"][night]["nightly_rate_cents"])
            for night in expected_dates
        )
        available = not missing and all(
            int(hotel["night_map"][night]["rooms_available"]) > 0
            for night in expected_dates
        )
        summaries.append({
            "hotel_id": hotel["hotel_id"],
            "name": hotel["name"],
            "postcode": hotel["postcode"],
            "check_in": first.isoformat(),
            "check_out": last.isoformat(),
            "included_nights": expected_dates,
            "nightly_rows": [hotel["night_map"][night] for night in expected_dates if night in hotel["night_map"]],
            "missing_dates": missing,
            "complete": not missing,
            "available_for_entire_stay": available,
            "total_cents": total_cents,
        })
    return summaries


def _sql_generation_prompt(question):
    return [
        {
            "role": "system",
            "content": (
                "You generate one safe, focused read-only SQLite SELECT for the user's question. "
                "Return exactly one JSON object with keys sql, stay, and postcode. sql must be one SELECT returning "
                "exactly these columns, in this order: hotel_id, name, postcode, stay_date, "
                "nightly_rate_cents, rooms_available. Keep one row per hotel ZIP nightly record; do not "
                "aggregate. Join only the documented tables. Include all matching saved-hotel nightly "
                "rows, not just a guessed winner. Set postcode to a five-digit ZIP only if the question "
                "asks about one ZIP; otherwise set postcode to null. Use LEFT JOIN for demo_hotel_nights "
                "so hotels with no night records remain visible. If a date or stay is requested, stay is "
                "required and must contain its exact ISO YYYY-MM-DD check_in and check_out dates; check-in "
                "is included and checkout is excluded, and a one-night question uses the next date as checkout. "
                "Put any date restriction only in the LEFT JOIN ON clause as stay_date >= check_in and "
                "stay_date < check_out. Never put a nightly-date restriction in WHERE, because that removes "
                "hotels with missing nights. If no date or stay is requested, set stay to null and include "
                "every nightly row. Include LIMIT 200 as the final clause. Do not use any functions, comments, "
                "PRAGMA, ATTACH, or additional statements. Return stay as {\"check_in\":\"...\",\"check_out\":\"...\"}. Never imply "
                "missing nightly records are available. Prices are simulated classroom data in integer cents. "
                "No Assignment 1 hotels, trips, users, bookings, or sample prices are in scope."
            ),
        },
        {
            "role": "user",
            "content": f"Allowlisted schema:\n{SCHEMA_DESCRIPTION}\n\nQuestion:\n{question}",
        },
    ]


def _answer_prompt(question, rows, stay_summaries):
    evidence = {
        "simulated_classroom_data": True,
        "nightly_records": rows[:MAX_TRACE_ROWS],
        "nightly_records_returned": len(rows),
        "stay_summaries_computed_from_actual_rows": stay_summaries,
    }
    return [
        {
            "role": "system",
            "content": (
                "Answer the user's question using only the supplied SQLite evidence. Do not invent hotel "
                "records, dates, prices, room counts, reservations, or completeness. Clearly label all "
                "prices and room availability as simulated classroom data. For multi-night stays, use only "
                "the server-computed summaries: check-in is included and checkout excluded. If missing_dates "
                "is nonempty, say the total or stay availability cannot be confirmed; never assume missing "
                "nights have rooms or a rate. If there are no matching records, say no matching saved hotel "
                "records were found. Mention the reason for any recommendation using evidence shown."
            ),
        },
        {
            "role": "user",
            "content": json.dumps({"question": question, "retrieved_evidence": evidence}, ensure_ascii=False),
        },
    ]


def _combine_empty_response_diagnostics(stage, initial_error, retry_error):
    initial = getattr(initial_error, "diagnostic", {})
    retry = getattr(retry_error, "diagnostic", {})
    message = f"The {stage} request returned no complete response after one retry."
    initial_summary = _diagnostic_summary(initial)
    retry_summary = _diagnostic_summary(retry)
    if initial_summary:
        message += f" Initial response: {initial_summary}."
    if retry_summary:
        message += f" Retry response: {retry_summary}."
    return LLMInvalidResponseError(
        message,
        {"initial_response": initial, "retry_response": retry},
    )


def _chat_completion_with_one_empty_retry(messages, max_tokens, stage):
    """Retry an empty or truncated completion once, keeping the same configured model."""
    try:
        content = _chat_completion(
            messages, max_tokens=max_tokens, stage=stage, reasoning_effort="none"
        )
        if not isinstance(content, str) or not content.strip():
            raise LLMEmptyResponseError(
                "The answer service returned an empty response.",
                {"stage": stage, "response_format": "empty_mock_response"},
            )
        return content
    except LLMEmptyResponseError as initial_error:
        retry_messages = list(messages)
        retry_messages[0] = dict(retry_messages[0])
        retry_messages[0]["content"] += (
            " Return the requested result in the user-facing message content. "
            "Do not return an empty message or a tool call."
        )
        retry_stage = f"{stage} retry"
        try:
            content = _chat_completion(
                retry_messages, max_tokens=max_tokens + 600,
                stage=retry_stage, reasoning_effort="none",
            )
            if not isinstance(content, str) or not content.strip():
                raise LLMEmptyResponseError(
                    "The answer service returned an empty response.",
                    {"stage": retry_stage, "response_format": "empty_mock_response"},
                )
            return content
        except (LLMEmptyResponseError, LLMInvalidResponseError, LLMProviderError) as retry_error:
            raise _combine_empty_response_diagnostics(stage, initial_error, retry_error) from None


def ask_saved_hotels(question, db_path=None):
    """Run generation, validation/retrieval, then a separate grounded answer call."""
    question = _safe_question(question)
    proposed_sql = None
    validation = "not run"
    rows = []
    summaries = []
    try:
        generated = _chat_completion_with_one_empty_retry(
            _sql_generation_prompt(question), max_tokens=1800, stage="SQL generation"
        )
        proposed_sql, stay, postcode = _parse_generation(generated)
        rows = execute_readonly_sql(
            proposed_sql, db_path=db_path, postcode=postcode, stay=stay
        )
        validation = "accepted: one bounded read-only SELECT over the saved-hotel allowlist"
        summaries = _derive_stays(rows, stay)
        answer = _chat_completion_with_one_empty_retry(
            _answer_prompt(question, rows, summaries),
            max_tokens=1800,
            stage="grounded answer",
        )
    except RagError:
        raise
    except ValueError as error:
        raise RagError(str(error)) from None

    return {
        "answer": answer,
        "simulated_classroom_data": True,
        "trace": {
            "question": question,
            "proposed_sql": proposed_sql,
            "validation_result": validation,
            "retrieved_records": rows[:MAX_TRACE_ROWS],
            "retrieved_record_count": len(rows),
            "derived_stays": summaries,
            "generated_answer": answer,
        },
    }
