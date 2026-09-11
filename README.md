# Expedia Lite — Assignment 1 Part 1

This repository contains **Part 1 only**: a Vue frontend, a FastAPI/Python backend, and CSV-based hotel search. It does **not** implement SQLite, bookings, booking history, or CRUD.

## What Part 1 does

- Provides a hotel-name search field and **Search** button in Vue.
- Sends the search request to FastAPI.
- Reads the supplied `hotels.csv` and `trips.csv` files in Python.
- Connects hotel and trip records using `hotel_id`.
- Displays matching hotel stays in a plain table with clear column labels.
- Shows a clear message when no matching hotel is found.

The supplied Part 1 data is already stored in `backend/data/`.

## Run the backend

From the project root:

```bash
cd backend
python -m venv .venv
```

Activate the virtual environment.

macOS/Linux:

```bash
source .venv/bin/activate
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install the backend dependency and start FastAPI:

```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Backend: `http://localhost:8000`

## Run the frontend

Open a second terminal from the project root:

```bash
cd frontend
npm install
npm run dev
```

Frontend: `http://localhost:5173`

## Part 1 verification

Use these checks in the browser:

1. Search for `Harbor Lantern Hotel`.
   - Expected: two stays appear: `T001` Boston Harbor Weekend and `T009` Boston Autumn Weekend.
2. Search for `zzzz-no-hotel`.
   - Expected: no result rows appear and the page shows a clear no-results message.
3. Record the action, expected result, and observed result in `report.md`.
4. Keep any verification screenshots in the repository and link them from `report.md` if used.

## Part 1 submission checkpoint

After manual review and browser verification:

```bash
git add .
git commit -m "Complete Assignment 1 Part 1 CSV search"
git push
git rev-parse HEAD
```

Put the repository URL and the exact commit hash into `report.md`, then upload `report.md` to the Part 1 submission page.
