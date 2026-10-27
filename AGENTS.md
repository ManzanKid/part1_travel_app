# Expedia Lite Agent Instructions

## Project

Expedia Lite is a local Vue + FastAPI application.

Part 1 implemented hotel search from CSV files.

Part 2 adds:

- SQLite persistence.
- Demo traveler selection.
- Simulated booking creation.
- Booking history.
- Booking cancellation while retaining the record.
- Booking deletion.
- MVC-style backend organization.

## Architecture

### View

The Vue frontend is in `frontend/`.

It communicates with the backend through HTTP requests and must not access SQLite directly.

### FastAPI

`backend/main.py` defines the API routes.

### Controller

`backend/controllers/database_controller.py` handles search and booking CRUD operations.

### Model

`backend/models/database.py` manages:

- SQLite connections.
- Database schema.
- Initial CSV seeding.
- Persistent application data.

## Data

The supplied starter files are:

- `hotels.csv`
- `trips.csv`
- `users.csv`
- `bookings.csv`

Use the CSV files only to seed SQLite when the database is first created.

Do not reload the CSV files on every startup because that would restore deleted records or duplicate starter data.

Preserve existing IDs and generate unique IDs for new bookings.

## Dependencies

Follow:

CHECK → TAKE ACTION → VERIFY

before adding dependencies.

Do not install `sqlite3` without first checking whether the selected Python interpreter already provides it.

## Verification

Part 2 must be verified through the frontend.

Check:

- Successful hotel search.
- Booking creation.
- Booking history.
- Booking cancellation.
- Persistence after browser refresh.
- Persistence after frontend/backend restart.
- Booking deletion.
- Persistence of deletion.

Record actual observed results in `report.md`.

## Git

Preserve the Part 1 checkpoint.

Part 2 was developed on the `part2-sqlite-crud` feature branch. The current Assignment 3.2 work is on `assignment3-part2`. Do not commit or push Assignment 3.2 until the student has reviewed and manually verified it.

## Assignment 3.2 — PausePath

PausePath is a separate Vue view and FastAPI/SQLite feature. Keep Expedia Lite search, map, booking, local hotel storage, and existing tests working. PausePath records use only `pausepath_sessions`, `pausepath_chat_threads`, `pausepath_chat_messages`, and `pausepath_preferences`; do not put PausePath records in hotel, trip, traveler, or booking tables.

PausePath is a coursework prototype for fictional scenarios only. It is not therapy, diagnosis, crisis monitoring, or a real mental health support service. Do not use real personal scenarios in tests. Keep Crisis information static and available from every PausePath screen without backend, model, or detection dependencies. It must explain that the app does not monitor or provide emergency assistance and list U.S. call/text 988 and immediate-emergency 911 information. Any phrase matching is incomplete and must not be presented as a reliable distress or clinical-risk detector.

The timed skill scripts are fixed in the frontend: six 4-second inhale / 6-second exhale cycles, and STOP in this order: Stop; Take a step back; Observe what is happening internally and externally; Proceed mindfully. A timer starts with the first displayed instruction, excludes pauses, and pauses on tab inactivity. Do not put an LLM request in the exercise path. Users can pause, resume, stop/leave, and reach Crisis information at all times.

Sessions and fictional conversations are saved only after explicit user action/consent. The optional recommendation can select only `breathing` or `stop`; it cannot generate exercise instructions or diagnoses, control timing, hide safety information, override the user's choice, or start an exercise. Use only the configured free model, with no paid fallback. Tests must mock model calls and use temporary SQLite databases.

### Assignment 3.2 verification commands

From `backend/`, activate `.venv` and run `EXPEDIA_LITE_DB_PATH=/private/tmp/pausepath-test.sqlite python -m unittest discover -s tests -v` to keep route-import initialization away from the application's database. From `frontend/`, run `npm test` for deterministic skill-rule tests and `npm run build` for the Vue production build. Do not install dependencies without user approval; `sqlite3` is part of Python's standard library.

On this workspace's Anaconda Node runtime, the npm `/usr/bin/env node` wrapper currently loses the temporary dynamic-library override. The direct Node/Vite equivalents that were verified are listed in the PausePath section of `README.md`; use a compatible Node/npm runtime for the standard commands elsewhere.

Record expected and observed browser/database behavior in `docs/assignment3/part32-verification.md`. Leave observed results blank until the student personally tests the application. Record test/build failures accurately and distinguish mocked tests from live model requests.
