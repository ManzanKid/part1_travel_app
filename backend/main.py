from pathlib import Path
import csv

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Expedia Lite - Part 1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
HOTELS_CSV = DATA_DIR / "hotels.csv"
TRIPS_CSV = DATA_DIR / "trips.csv"


def read_csv(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing data file: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


@app.get("/")
def root():
    return {"message": "Expedia Lite Part 1 API is running"}


@app.get("/api/search")
def search_hotels(hotel_name: str = Query(..., min_length=1)):
    hotels = read_csv(HOTELS_CSV)
    trips = read_csv(TRIPS_CSV)

    term = hotel_name.strip().lower()
    matching_hotels = [
        hotel for hotel in hotels
        if term in hotel.get("hotel_name", "").lower()
    ]

    hotel_by_id = {hotel["hotel_id"]: hotel for hotel in matching_hotels}
    results = []

    for trip in trips:
        hotel = hotel_by_id.get(trip.get("hotel_id"))
        if not hotel:
            continue

        results.append({
            "hotel_id": hotel.get("hotel_id", ""),
            "hotel_name": hotel.get("hotel_name", ""),
            "city": hotel.get("city", ""),
            "state": hotel.get("state", ""),
            "nightly_rate_usd": hotel.get("nightly_rate_usd", ""),
            "trip_id": trip.get("trip_id", ""),
            "trip_name": trip.get("trip_name", ""),
            "check_in": trip.get("check_in", ""),
            "check_out": trip.get("check_out", ""),
        })

    return {"query": hotel_name, "count": len(results), "results": results}
