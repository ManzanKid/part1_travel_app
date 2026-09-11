# Part 1 design note

The Vue frontend owns user interaction and rendering. It accepts a hotel-name query and calls the FastAPI backend.

FastAPI owns the HTTP API and CSV data access. The `/api/search` route reads `hotels.csv` and `trips.csv`, filters hotels by hotel name, joins records by `hotel_id`, and sends matching stays back as JSON.

The backend remains the data boundary; the frontend does not read CSV files directly.
