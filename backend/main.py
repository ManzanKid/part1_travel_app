from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pydantic import Field
from config import geoapify_config_status
from controllers.hotel_discovery_controller import discover_hotels

from models.database import initialize_database
from controllers.database_controller import (
    search_hotels,
    get_users,
    get_booking_history,
    create_booking,
    cancel_booking,
    delete_booking,
    save_api_hotel,
    get_saved_hotels,
    remove_saved_hotel,
    is_hotel_saved,
)
from controllers.geoapify_controller import (
    lookup_postcode,
    ZipNotFoundError,
    GeoapifyRequestError,
    GeoapifyConfigurationError,
      InvalidZipError,
)
from controllers.hotel_rag_controller import (
    ask_saved_hotels,
    RagError,
    RagConfigurationError,
    LLMRateLimitError,
    LLMProviderError,
    LLMInvalidResponseError,
    SQLRejectedError,
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


class SavedHotelCreate(BaseModel):
    hotel: dict
    postcode: str
    location: dict


class HotelQuestion(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)


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


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "geoapify": geoapify_config_status()
    }


@app.get("/api/local/hotels")
def api_saved_hotels(postcode: str = Query(..., min_length=5, max_length=5)):
    if not postcode.isdigit():
        raise HTTPException(status_code=422, detail="Enter a valid five-digit U.S. ZIP code.")
    hotels = get_saved_hotels(postcode)
    if hotels:
        first = hotels[0]
        location = {"postcode": postcode, "locality": first["locality"], "country_code": first["country_code"], "latitude": first["location_latitude"], "longitude": first["location_longitude"]}
    else:
        location = None
    return {"location": location, "count": len(hotels), "hotels": hotels}


@app.post("/api/local/hotels")
def api_save_hotel(payload: SavedHotelCreate):
    try:
        saved = save_api_hotel(payload.hotel, payload.postcode, payload.location)
        return saved
    except (ValueError, KeyError, TypeError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from None


@app.delete("/api/local/hotels/{hotel_id}")
def api_remove_hotel(hotel_id: str):
    try:
        return remove_saved_hotel(hotel_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from None


@app.get("/api/local/hotels/{hotel_id}/saved")
def api_hotel_saved(hotel_id: str):
    return {"saved": is_hotel_saved(hotel_id)}


@app.post("/api/chatbot/ask")
def api_ask_saved_hotels(payload: HotelQuestion):
    try:
        return ask_saved_hotels(payload.question)
    except RagConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from None
    except LLMRateLimitError as error:
        raise HTTPException(status_code=429, detail=str(error)) from None
    except (LLMProviderError, LLMInvalidResponseError) as error:
        raise HTTPException(status_code=502, detail=str(error)) from None
    except SQLRejectedError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    except RagError as error:
        raise HTTPException(status_code=400, detail=str(error)) from None
@app.get("/api/demo/zip-location")
def demo_zip_location():
    try:
        return lookup_postcode("16802")

    except GeoapifyConfigurationError:
        raise HTTPException(
            status_code=503,
            detail="Location lookup is not configured"
        ) from None

    except ZipNotFoundError:
     raise HTTPException(
            status_code=404,
            detail="ZIP code 16802 could not be resolved"
        ) from None

    except GeoapifyRequestError:
        raise HTTPException(
            status_code=502,
            detail="Location lookup service is unavailable"
        ) from None
    
@app.get("/api/discovery/hotels")
def discover_nearby_hotels(postcode: str):
    try:
        return discover_hotels(postcode)

    except InvalidZipError:
        raise HTTPException(
            status_code=422,
            detail="Enter a valid five-digit U.S. ZIP code."
        ) from None

    except ZipNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="The requested U.S. ZIP code could not be resolved."
        ) from None

    except GeoapifyConfigurationError:
        raise HTTPException(
            status_code=503,
            detail="Hotel discovery is not configured."
        ) from None

    except GeoapifyRequestError:
        raise HTTPException(
            status_code=502,
            detail="Hotel discovery service is unavailable."
        ) from None
