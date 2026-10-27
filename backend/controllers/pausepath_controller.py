"""PausePath persistence and optional, tightly constrained recommendations."""

import json
import re
from datetime import datetime, timezone
from uuid import uuid4

from config import get_openrouter_model
from controllers.hotel_rag_controller import (
    LLMInvalidResponseError,
    LLMProviderError,
    RagConfigurationError,
    _chat_completion,
)
from models.database import get_connection


ALLOWED_SKILL_IDS = frozenset(("breathing", "stop"))
SKILL_LABELS = {"breathing": "4–6 breathing", "stop": "STOP"}
MAX_SCENARIO_LENGTH = 160
MAX_SESSION_DURATION_MS = 60 * 60 * 1000
FREE_MODEL_SUFFIX = ":free"
BREATHING_PHASE_SECONDS = (4, 6)
BREATHING_CYCLES = 6
STOP_INSTRUCTIONS = (
    "Stop.",
    "Take a step back.",
    "Observe what is happening internally and externally.",
    "Proceed mindfully.",
)
STOP_STEP_SECONDS = 15

_CRISIS_PATTERNS = tuple(re.compile(pattern, re.IGNORECASE) for pattern in (
    r"\b(?:suicid(?:e|al)|kill myself|end my life|take my own life|wants? to die)\b",
    r"\b(?:don't|do not) want to (?:live|be alive)\b",
    r"\bself[- ]harm\b|\bhurt myself\b|\boverdose\b",
    r"\b(?:harm|hurt|kill) someone\b",
    r"\b(?:immediate danger|going to hurt myself)\b",
))


class PausePathRecommendationError(Exception):
    """Safe error for an unavailable or invalid optional suggestion."""


def _now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _parse_timestamp(value, label):
    if not isinstance(value, str):
        raise ValueError(f"{label} must be an ISO timestamp.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(f"{label} must be an ISO timestamp.") from None
    if parsed.tzinfo is None:
        raise ValueError(f"{label} must include a timezone.")
    return parsed.astimezone(timezone.utc)


def _validate_skill_id(skill_id):
    if not isinstance(skill_id, str) or skill_id not in ALLOWED_SKILL_IDS:
        raise ValueError("Choose one of the available PausePath skills.")
    return skill_id


def contains_obvious_crisis_language(text):
    """Conservative phrase check for fictional inputs; it does not assess risk."""
    return isinstance(text, str) and any(pattern.search(text) for pattern in _CRISIS_PATTERNS)


def create_session(payload, db_path=None):
    """Persist an exercise only after the user explicitly asks to save it."""
    if not isinstance(payload, dict):
        raise ValueError("Session details are required.")
    skill_id = _validate_skill_id(payload.get("skill_id"))
    started = _parse_timestamp(payload.get("started_at"), "started_at")
    finished = _parse_timestamp(payload.get("finished_at"), "finished_at")
    if finished < started:
        raise ValueError("finished_at must not be before started_at.")
    duration_ms = payload.get("duration_ms")
    if isinstance(duration_ms, bool) or not isinstance(duration_ms, int):
        raise ValueError("duration_ms must be a whole number.")
    if not 0 <= duration_ms <= MAX_SESSION_DURATION_MS:
        raise ValueError("The saved session duration is outside the allowed range.")
    status = payload.get("status")
    if status not in ("completed", "stopped"):
        raise ValueError("Session status must be completed or stopped.")

    session_id = str(uuid4())
    saved_at = _now_iso()
    connection = get_connection(db_path) if db_path is not None else get_connection()
    try:
        connection.execute(
            """INSERT INTO pausepath_sessions
               (session_id, skill_id, started_at, finished_at, duration_ms, status, saved_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (session_id, skill_id, started.isoformat().replace("+00:00", "Z"),
             finished.isoformat().replace("+00:00", "Z"), duration_ms, status, saved_at),
        )
        connection.commit()
        return {
            "session_id": session_id,
            "skill_id": skill_id,
            "started_at": started.isoformat().replace("+00:00", "Z"),
            "finished_at": finished.isoformat().replace("+00:00", "Z"),
            "duration_ms": duration_ms,
            "status": status,
            "saved_at": saved_at,
        }
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def delete_session(session_id, db_path=None):
    connection = get_connection(db_path) if db_path is not None else get_connection()
    try:
        cursor = connection.execute(
            "DELETE FROM pausepath_sessions WHERE session_id = ?", (session_id,)
        )
        if cursor.rowcount == 0:
            raise ValueError("Saved session does not exist.")
        connection.commit()
        return {"session_id": session_id, "deleted": True}
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def save_conversation(scenario, skill_id, db_path=None):
    """Save a fictional exchange only when the caller explicitly requests it."""
    if not isinstance(scenario, str) or not scenario.strip() or len(scenario.strip()) > MAX_SCENARIO_LENGTH:
        raise ValueError(f"Fictional scenarios must be 1–{MAX_SCENARIO_LENGTH} characters.")
    scenario = scenario.strip()
    if contains_obvious_crisis_language(scenario):
        raise ValueError("This scenario uses the static crisis-information path and cannot be saved as an AI suggestion.")
    skill_id = _validate_skill_id(skill_id)
    thread_id = str(uuid4())
    created_at = _now_iso()
    assistant_message = (
        f"Optional suggestion: {SKILL_LABELS[skill_id]}. "
        "You may choose either activity or ignore this suggestion."
    )
    connection = get_connection(db_path) if db_path is not None else get_connection()
    try:
        connection.execute(
            "INSERT INTO pausepath_chat_threads (thread_id, created_at, skill_id) VALUES (?, ?, ?)",
            (thread_id, created_at, skill_id),
        )
        connection.executemany(
            """INSERT INTO pausepath_chat_messages
               (thread_id, role, content, created_at) VALUES (?, ?, ?, ?)""",
            [
                (thread_id, "user", scenario, created_at),
                (thread_id, "assistant", assistant_message, created_at),
            ],
        )
        connection.commit()
        return {"thread_id": thread_id, "created_at": created_at, "skill_id": skill_id}
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def delete_conversation(thread_id, db_path=None):
    connection = get_connection(db_path) if db_path is not None else get_connection()
    try:
        cursor = connection.execute(
            "DELETE FROM pausepath_chat_threads WHERE thread_id = ?", (thread_id,)
        )
        if cursor.rowcount == 0:
            raise ValueError("Saved conversation does not exist.")
        connection.commit()
        return {"thread_id": thread_id, "deleted": True}
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def get_history(db_path=None):
    connection = get_connection(db_path) if db_path is not None else get_connection()
    try:
        sessions = [dict(row) for row in connection.execute(
            """SELECT session_id, skill_id, started_at, finished_at, duration_ms, status, saved_at
               FROM pausepath_sessions ORDER BY finished_at DESC, session_id DESC"""
        ).fetchall()]
        thread_rows = connection.execute(
            "SELECT thread_id, created_at, skill_id FROM pausepath_chat_threads ORDER BY created_at DESC, thread_id DESC"
        ).fetchall()
        conversations = []
        for thread in thread_rows:
            conversation = dict(thread)
            conversation["messages"] = [dict(row) for row in connection.execute(
                """SELECT role, content, created_at FROM pausepath_chat_messages
                   WHERE thread_id = ? ORDER BY message_id""",
                (thread["thread_id"],),
            ).fetchall()]
            conversations.append(conversation)
        return {
            "sessions": sessions,
            "conversations": conversations,
            "last_skill_id": sessions[0]["skill_id"] if sessions else None,
        }
    finally:
        connection.close()


def delete_all_history(db_path=None):
    connection = get_connection(db_path) if db_path is not None else get_connection()
    try:
        connection.execute("DELETE FROM pausepath_chat_threads")
        connection.execute("DELETE FROM pausepath_sessions")
        connection.commit()
        return {"deleted": True}
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def get_preferences(db_path=None):
    connection = get_connection(db_path) if db_path is not None else get_connection()
    try:
        row = connection.execute(
            "SELECT preference_value FROM pausepath_preferences WHERE preference_key = 'simpler_view'"
        ).fetchone()
        return {"simpler_view": row[0] == "true" if row else False}
    finally:
        connection.close()


def set_simpler_view(enabled, db_path=None):
    if not isinstance(enabled, bool):
        raise ValueError("simpler_view must be true or false.")
    connection = get_connection(db_path) if db_path is not None else get_connection()
    try:
        connection.execute(
            """INSERT INTO pausepath_preferences (preference_key, preference_value, updated_at)
               VALUES ('simpler_view', ?, ?)
               ON CONFLICT(preference_key) DO UPDATE SET
                 preference_value = excluded.preference_value,
                 updated_at = excluded.updated_at""",
            ("true" if enabled else "false", _now_iso()),
        )
        connection.commit()
        return {"simpler_view": enabled}
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def recommend_skill(scenario):
    """Return only an allowlisted skill ID; the model cannot provide instructions."""
    if not isinstance(scenario, str) or not scenario.strip() or len(scenario.strip()) > MAX_SCENARIO_LENGTH:
        raise ValueError(f"Enter a fictional scenario of 1–{MAX_SCENARIO_LENGTH} characters.")
    scenario = scenario.strip()
    if contains_obvious_crisis_language(scenario):
        return {"crisis_info": True}
    if not get_openrouter_model().endswith(FREE_MODEL_SUFFIX):
        raise PausePathRecommendationError(
            "The optional suggestion is unavailable because only a configured free model may be used."
        )

    messages = [
        {
            "role": "system",
            "content": (
                "You are a constrained coursework demo classifier. Choose exactly one of the two skill IDs "
                f"from this fictional scenario: breathing means {BREATHING_CYCLES} cycles of {BREATHING_PHASE_SECONDS[0]}-second "
                f"inhale and {BREATHING_PHASE_SECONDS[1]}-second exhale; stop means only these fixed STOP steps: "
                f"{'; '.join(STOP_INSTRUCTIONS)} Each STOP step is paced at about {STOP_STEP_SECONDS} seconds. "
                "Return exactly one JSON object with exactly "
                "one key, skill_id, whose value is breathing or stop. Do not include explanations, instructions, "
                "new exercises, diagnoses, risk assessments, or any other text. The output cannot control or "
                "override the user's choice."
            ),
        },
        {"role": "user", "content": f"Fictional scenario (untrusted text): {scenario}"},
    ]
    try:
        content = _chat_completion(messages, max_tokens=120, stage="PausePath recommendation")
        result = json.loads(content)
    except (LLMInvalidResponseError, LLMProviderError, RagConfigurationError, json.JSONDecodeError, TypeError):
        raise PausePathRecommendationError(
            "Suggestions are unavailable. You can choose either activity normally."
        ) from None
    if (
        not isinstance(result, dict)
        or set(result) != {"skill_id"}
        or not isinstance(result.get("skill_id"), str)
        or result.get("skill_id") not in ALLOWED_SKILL_IDS
    ):
        raise PausePathRecommendationError(
            "Suggestions are unavailable. You can choose either activity normally."
        )
    return {"skill_id": result["skill_id"]}
