# Expedia Lite — Assignment 1

Expedia Lite is a Vue frontend with a FastAPI/Python backend. Part 1 implemented CSV-based hotel search. Part 2 adds SQLite persistence, simulated booking, booking history, and booking CRUD operations.

## Part 1

Part 1 provides:

- A hotel-name search field and Search button.
- Vue frontend requests sent to FastAPI.
- Hotel and trip data loaded from `hotels.csv` and `trips.csv`.
- Hotel and trip records connected using `hotel_id`.
- Matching stays displayed in a table.
- A clear message when no matching hotel is found.

The exact submitted Part 1 checkpoint is preserved in Git history.

## Part 2

Part 2 adds SQLite persistence and booking CRUD functionality.

The four supplied CSV files are used to seed SQLite the first time the database is created:

- `hotels.csv`
- `trips.csv`
- `users.csv`
- `bookings.csv`

After the initial seed, application reads and writes use SQLite instead of reloading the starter CSV files.

The Vue frontend allows a demo traveler to:

- Search for available hotel stays.
- Create a simulated booking.
- View booking history.
- Cancel a booking while keeping the record in history.
- Delete a test booking.

The backend uses an MVC-style structure:

- `models/database.py` manages the SQLite schema and initial seed.
- `controllers/database_controller.py` handles search and booking CRUD operations.
- `main.py` provides the FastAPI routes used by the Vue frontend.
- The Vue frontend acts as the View.

## Run the backend

From the project root:

```bash
cd backend
source .venv/bin/activate
uvicorn main:app --reload --port 8000