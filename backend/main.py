from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from models.database import initialize_database
from controllers.database_controller import (
    search_hotels,
    get_users,
    get_booking_history,
    create_booking,
    cancel_booking,
    delete_booking,
)


initialize_database()

app = FastAPI(title="Expedia Lite - Part 2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class BookingCreate(BaseModel):
    user_id: str
    trip_id: str


@app.get("/")
def root():
    return {"message": "Expedia Lite Part 2 API is running"}


@app.get("/api/search")
def api_search(hotel_name: str = Query(..., min_length=1)):
    results = search_hotels(hotel_name)

    return {
        "query": hotel_name,
        "count": len(results),
        "results": results,
    }


@app.get("/api/users")
def api_users():
    return {"users": get_users()}


@app.get("/api/bookings")
def api_booking_history(user_id: str = Query(..., min_length=1)):
    bookings = get_booking_history(user_id)

    return {
        "user_id": user_id,
        "count": len(bookings),
        "bookings": bookings,
    }


@app.post("/api/bookings")
def api_create_booking(booking: BookingCreate):
    try:
        return create_booking(
            booking.user_id,
            booking.trip_id,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@app.patch("/api/bookings/{booking_id}/cancel")
def api_cancel_booking(booking_id: str):
    try:
        return cancel_booking(booking_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))


@app.delete("/api/bookings/{booking_id}")
def api_delete_booking(booking_id: str):
    try:
        return delete_booking(booking_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))