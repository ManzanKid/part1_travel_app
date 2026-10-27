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

## PausePath (Assignment 3.2)

PausePath is a separate coursework prototype available from the application switcher. Expedia Lite stays available in its own view. PausePath is for **fictional scenarios only**; it is not therapy, diagnosis, crisis monitoring, or a real mental health support service.

PausePath provides two fixed activities:

- **4–6 breathing:** six cycles of a four-second inhale and six-second exhale (60 seconds at the intended pace).
- **STOP:** Stop, Take a step back, Observe what is happening internally and externally, Proceed mindfully (about 60 seconds at the intended pace).

The timer starts when the first instruction is shown. Pause time, time viewing crisis information, and time while the browser tab is inactive are excluded. The tab automatically pauses an exercise when it becomes inactive. Pause, Resume, Stop / Leave, and Crisis information controls are available without an LLM request. Reduced motion is supported; the instructions and countdown do not rely on animation.

Saving a session requires clicking **Save this session to history**. A fictional scenario and suggestion are not stored unless **Save this fictional exchange to history** was checked before requesting the optional suggestion. Saved sessions and conversations can be reviewed and deleted. PausePath uses separate `pausepath_sessions`, `pausepath_chat_threads`, `pausepath_chat_messages`, and `pausepath_preferences` tables; it does not store PausePath data in hotel tables.

**Crisis information is static and does not depend on the backend or model.** In the United States, call or text 988 for crisis support, or call 911 for immediate emergencies. PausePath does not monitor users or provide emergency assistance. Its limited phrase check is incomplete, can miss or overflag wording, and does not determine anyone's risk.

The optional **Help me choose** feature sends a fictional scenario of up to 160 characters to the configured backend model. The backend only accepts the `breathing` and `stop` skill IDs. It does not accept generated exercise instructions or diagnoses, does not choose for the user, and does not automatically start an exercise. The recommendation endpoint rejects configured model IDs without the `:free` suffix; no paid fallback is configured. If the model is unavailable or returns invalid output, choose either activity directly. The timed exercise does not initiate or depend on a model request.

### Run PausePath

Start the backend in one terminal:

```bash
cd backend
source .venv/bin/activate
uvicorn main:app --reload --port 8000
```

Start the frontend in another terminal:

```bash
cd frontend
npm run dev
```

Open `http://localhost:5173/`; PausePath opens first. Use the application switcher to return to Expedia Lite. The static exercises and crisis-information screen do not require OpenRouter configuration. The optional suggestion uses the same backend-only OpenRouter key and configured free model described above for the hotel assistant.

On a compatible Node/npm installation, use `npm run dev` as shown above. This workspace's Anaconda `npm` wrapper currently drops a required dynamic-library override; to launch Vite here without changing or installing packages, run from `frontend/`:

```bash
env DYLD_INSERT_LIBRARIES=/opt/anaconda3/lib/libsqlite3.3.53.4.dylib DYLD_FORCE_FLAT_NAMESPACE=1 /opt/anaconda3/bin/node node_modules/vite/bin/vite.js --host 127.0.0.1
```

### Test PausePath and Expedia Lite

Backend tests use temporary databases and mocked model responses. To keep the application's ignored database separate when FastAPI routes are imported by the tests, use a disposable database path:

```bash
cd backend
source .venv/bin/activate
EXPEDIA_LITE_DB_PATH=/private/tmp/pausepath-test.sqlite python -m unittest discover -s tests -v
```

Frontend deterministic timing-rule tests and the production build commands are:

```bash
cd frontend
npm test
npm run build
```

On this workspace's Anaconda Node setup, the equivalent checks that passed were run directly through Node to keep the one-process library override:

```bash
cd frontend
env DYLD_INSERT_LIBRARIES=/opt/anaconda3/lib/libsqlite3.3.53.4.dylib DYLD_FORCE_FLAT_NAMESPACE=1 /opt/anaconda3/bin/node --test tests/pausepathRules.test.mjs
env DYLD_INSERT_LIBRARIES=/opt/anaconda3/lib/libsqlite3.3.53.4.dylib DYLD_FORCE_FLAT_NAMESPACE=1 /opt/anaconda3/bin/node node_modules/vite/bin/vite.js build --outDir /private/tmp/pausepath-vite-build
```

No additional package is required for PausePath. Before submission, complete the manual checks in [the Assignment 3.2 verification sheet](docs/assignment3/part32-verification.md); its observed-results column is intentionally blank until the student verifies the browser and persistence behavior.
