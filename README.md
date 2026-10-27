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
```

## Run the frontend

From the project root, use another terminal:

```bash
cd frontend
npm run dev
```

Open `http://localhost:5173/`.

## Geoapify Configuration

The Geoapify API key is stored in the `.env` file in the
project root, alongside `frontend/` and `backend/`.

The backend uses `python-dotenv` to load this configuration.

The `.env` file is excluded from Git to protect the API key.

After adding or changing the API key in `.env`, restart the
FastAPI backend so it loads the updated configuration.

The `/api/health` endpoint reports whether the key is configured
without displaying the key itself.

This configuration check does not make a Geoapify API request.

## Saved hotel assistant (Assignment 2 Part 2)

The chatbot answers questions using locally saved hotels and their simulated `demo_hotel_nights` records. Its backend flow asks the configured OpenRouter model for one bounded SELECT, validates and runs that query against SQLite in read-only mode, and makes a second model request with only the retrieved records and server-computed stay totals. The assistant does not create or change bookings.

Add an OpenRouter API key to the ignored project-root `.env` file:

```dotenv
OPENROUTER_API_KEY=your_key_here
OPENROUTER_MODEL=nvidia/nemotron-3.5-lightning:free
```

`OPENROUTER_MODEL` is optional and can be changed when free model availability changes. Restart FastAPI after changing `.env`. The API key is used only by the backend and is never returned to the browser. No additional packages are required for the assistant.

The endpoint is `POST /api/chatbot/ask` with JSON `{ "question": "Which saved hotel is cheapest?" }`. Its response includes an answer and a bounded verification trace with the question, proposed SQL, validation result, retrieved rows, and generated answer. All room counts and prices shown by the assistant are simulated classroom data.

See [the RAG research and security notes](docs/assignment2-part2-research.md) and [the early chatbot mockup](docs/assignment2-part2-chatbot-mockup.svg).
