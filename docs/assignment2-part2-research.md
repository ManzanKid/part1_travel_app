# Assignment 2 Part 2 — SQL RAG Research and Design

## Research date

October 27, 2026.

## LLM provider and model

Use OpenRouter's OpenAI-compatible Chat Completions API from FastAPI. The default is `nvidia/nemotron-3.5-lightning:free`, selected from OpenRouter's current free model catalog. `OPENROUTER_MODEL` will override the model without a code change. Both stages use an 1,800-token output budget and `reasoning.effort=none` with reasoning excluded, so reasoning cannot consume the whole visible answer budget. Free model availability, rate limits, latency, output behavior, and model IDs can change; keep the model setting configurable and return a useful service error when the provider is unavailable. The OpenRouter key is read only by the backend from the project's ignored `.env` file.

References:

- OpenRouter free model catalog: https://openrouter.ai/collections/free-models/
- Nemotron 3.5 Lightning listing: https://openrouter.ai/nvidia/nemotron-3.5-lightning:free/
- OpenRouter Chat Completions API: https://openrouter.ai/docs/api/api-reference/chat/send-chat-completion-request

## Retrieval approach

This is SQL-based retrieval over the saved hotel corpus, not vector search. The first model request receives the question, a small allowlisted schema description, and explicit date, availability, price, and read-only rules. It must return a JSON object containing a single proposed SELECT query. FastAPI parses the object and validates the query locally. Only then does a SQLite read-only connection retrieve rows from `saved_hotels`, `saved_hotel_locations`, and `demo_hotel_nights`. The server sends the original question and bounded retrieved records to a second model request for a grounded natural-language answer.

The server, not the model, owns the SQLite connection and enforces authorization. SQL preparation uses SQLite's authorizer callback with a table, column, and function allowlist, plus query-only mode and read-only URI connections. The validator also requires a small top-level row limit, rejects statement tails, and applies an execution progress deadline and a result cap. Returned rows are compared with a fixed, parameterized read-only query over the same matching scope, so fabricated or incomplete result sets are rejected. A second request is never made if SQL generation, parsing, validation, or retrieval fails. Missing dates stay missing; totals and availability are derived from actual returned nightly rows and never filled in with assumptions.

## Security and privacy decisions

- Keep `OPENROUTER_API_KEY` on the backend; never return it in responses, traces, logs, tests, or screenshots.
- Send only the user's question, limited schema description, SQL proposal context, and retrieved saved-hotel records. Do not send Assignment 1 users, trips, bookings, or database files.
- Treat model output and retrieved text as untrusted data. Escape/serialize it as JSON in the second request; do not execute model-produced prose.
- Permit only a single bounded SELECT over three saved-hotel tables; reject write operations, other tables, unsafe SQLite functions, PRAGMA, ATTACH, and additional statements.
- Use `mode=ro`, SQLite query-only enforcement, an authorizer callback, maximum row limits, and a SQLite progress handler. Never open the live database for writes during chatbot retrieval.
- Show proposed SQL and retrieved rows in a bounded verification trace for local debugging, while omitting credentials and applying response-size limits.
- The LLM can make incorrect SQL or wording. Server-side checks and direct record grounding reduce, but do not eliminate, this risk.

## Price, dates, and availability rules

`nightly_rate_cents` is the sole source for simulated local prices. For a stay from check-in through checkout, include check-in and exclude checkout. A complete stay requires one nightly row for every included date. Total cost is computed from those rows in Python using integer cents. A room is available for the whole stay only if every included night exists and has `rooms_available > 0`. A missing row means unknown/incomplete data, never availability. All such values are labeled simulated classroom data in the UI and answer instructions. Assignment 1 sample prices and bookings are outside this RAG corpus.

## Dependencies

No new packages are planned. Python's existing `sqlite3`, `urllib`, `json`, `datetime`, and `unittest` modules cover database authorization, HTTP, parsing, date arithmetic, and tests. `python-dotenv` is already listed in `backend/requirements.txt` and is used to read the ignored project `.env`. The Vue app already has the required framework and build dependencies.

## Interface design

The early mockup is `docs/assignment2-part2-chatbot-mockup.svg`. It places an accessible question form and answer/trace panel after the current ZIP hotel discovery panel, preserving the existing application layout and map. The local-first list/map and booking sections remain intact.

### Design changes during implementation

The Vue implementation follows the mockup's placement and form/answer layout. It uses a native collapsed `<details>` section for the potentially long verification trace rather than showing raw SQL and records by default. It also adds explicit inline notices when no records match or when requested nightly data is incomplete, so the model's answer is accompanied by a deterministic data-status message.

## Limitations

- This is a classroom demonstration, not a booking or inventory service.
- The nightly data is simulated and may cover only a few seeded demo dates.
- Free model routing can be rate-limited or unavailable, and provider-side model changes may alter output quality.
- SQL validation controls what can run, but cannot guarantee that the generated question interpretation is correct.
- A grounded answer can summarize only records retrieved from the saved hotel tables; it cannot discover unsaved hotels or use Assignment 1 bookings.
- The answer is not a complete list of area hotels and should not imply that local saved data is comprehensive.
