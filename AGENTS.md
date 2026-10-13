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

Develop Part 2 on the `part2-sqlite-crud` feature branch.

After review and verification:

1. Commit the feature branch.
2. Merge it into `main`.
3. Check the combined application.
4. Push the final Part 2 commit.