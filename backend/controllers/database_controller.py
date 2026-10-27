from datetime import date

from models.database import get_connection


def save_api_hotel(hotel, postcode, location):
    """Save a provider hotel, its searched ZIP context, and demo nights."""
    hotel_id = str(hotel.get("place_id") or hotel.get("hotel_id") or "").strip()
    if not hotel_id:
        raise ValueError("Hotel provider ID is required.")
    try:
        latitude = float(hotel["latitude"])
        longitude = float(hotel["longitude"])
    except (KeyError, TypeError, ValueError):
        raise ValueError("Hotel coordinates are required.") from None
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise ValueError("Hotel coordinates are invalid.")
    if not postcode or not postcode.isdigit() or len(postcode) != 5:
        raise ValueError("A five-digit searched ZIP is required.")
    connection = get_connection()
    try:
        connection.execute(
            "INSERT OR IGNORE INTO saved_hotels (hotel_id, name, address, latitude, longitude) VALUES (?, ?, ?, ?, ?)",
            (hotel_id, hotel.get("name"), hotel.get("address"), latitude, longitude),
        )
        connection.execute(
            "INSERT OR IGNORE INTO saved_hotel_locations (hotel_id, postcode, locality, country_code, latitude, longitude) VALUES (?, ?, ?, ?, ?, ?)",
            (hotel_id, postcode, location.get("locality"), location.get("country_code", "us"), float(location["latitude"]), float(location["longitude"])),
        )
        for day in range(10, 15):
            connection.execute(
                "INSERT OR IGNORE INTO demo_hotel_nights (hotel_id, stay_date) VALUES (?, ?)",
                (hotel_id, f"2026-10-{day:02d}"),
            )
        connection.commit()
        return {"place_id": hotel_id, "saved": True}
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def get_saved_hotels(postcode):
    connection = get_connection()
    try:
        hotels = connection.execute(
            """SELECT h.hotel_id AS place_id, h.name, h.address, h.latitude, h.longitude,
                      l.postcode, l.locality, l.country_code, l.latitude AS location_latitude,
                      l.longitude AS location_longitude
               FROM saved_hotels h JOIN saved_hotel_locations l ON l.hotel_id = h.hotel_id
               WHERE l.postcode = ? ORDER BY h.name, h.hotel_id""", (postcode,)
        ).fetchall()
        result = []
        for row in hotels:
            hotel = dict(row)
            hotel["distance_meters"] = None
            hotel["nights"] = [dict(night) for night in connection.execute(
                "SELECT stay_date, nightly_rate_cents, rooms_available FROM demo_hotel_nights WHERE hotel_id = ? ORDER BY stay_date",
                (hotel["place_id"],),
            ).fetchall()]
            result.append(hotel)
        return result
    finally:
        connection.close()


def remove_saved_hotel(hotel_id):
    connection = get_connection()
    try:
        cursor = connection.execute("DELETE FROM saved_hotels WHERE hotel_id = ?", (hotel_id,))
        if not cursor.rowcount:
            raise ValueError("Saved hotel does not exist.")
        connection.commit()
        return {"place_id": hotel_id, "deleted": True}
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def is_hotel_saved(hotel_id):
    connection = get_connection()
    try:
        return connection.execute("SELECT 1 FROM saved_hotels WHERE hotel_id = ?", (hotel_id,)).fetchone() is not None
    finally:
        connection.close()


def search_hotels(hotel_name):
    """Search hotel stays by hotel name."""
    term = f"%{hotel_name.strip().lower()}%"

    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT
                h.hotel_id,
                h.hotel_name,
                h.city,
                h.state,
                h.nightly_rate_usd,
                t.trip_id,
                t.trip_name,
                t.check_in,
                t.check_out
            FROM hotels h
            JOIN trips t ON h.hotel_id = t.hotel_id
            WHERE LOWER(h.hotel_name) LIKE ?
            ORDER BY t.check_in
            """,
            (term,),
        ).fetchall()

        return [dict(row) for row in rows]

    finally:
        connection.close()


def get_users():
    """Return all demo travelers."""
    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT user_id, display_name
            FROM users
            ORDER BY user_id
            """
        ).fetchall()

        return [dict(row) for row in rows]

    finally:
        connection.close()


def get_booking_history(user_id):
    """Return booking history for one demo traveler."""
    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT
                b.booking_id,
                b.user_id,
                b.trip_id,
                b.booked_on,
                b.status,
                t.trip_name,
                t.check_in,
                t.check_out,
                h.hotel_name,
                h.city,
                h.state,
                h.nightly_rate_usd
            FROM bookings b
            JOIN trips t ON b.trip_id = t.trip_id
            JOIN hotels h ON t.hotel_id = h.hotel_id
            WHERE b.user_id = ?
            ORDER BY b.booking_id
            """,
            (user_id,),
        ).fetchall()

        return [dict(row) for row in rows]

    finally:
        connection.close()


def _next_booking_id(connection):
    """Generate the next unused booking ID such as B007."""
    rows = connection.execute(
        "SELECT booking_id FROM bookings"
    ).fetchall()

    highest = 0

    for row in rows:
        booking_id = row["booking_id"]

        if booking_id.startswith("B") and booking_id[1:].isdigit():
            highest = max(highest, int(booking_id[1:]))

    return f"B{highest + 1:03d}"


def create_booking(user_id, trip_id):
    """Create and save a new confirmed booking."""
    connection = get_connection()

    try:
        user = connection.execute(
            "SELECT user_id FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()

        if user is None:
            raise ValueError("User does not exist.")

        trip = connection.execute(
            "SELECT trip_id FROM trips WHERE trip_id = ?",
            (trip_id,),
        ).fetchone()

        if trip is None:
            raise ValueError("Trip does not exist.")

        booking_id = _next_booking_id(connection)

        connection.execute(
            """
            INSERT INTO bookings
                (booking_id, user_id, trip_id, booked_on, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                booking_id,
                user_id,
                trip_id,
                date.today().isoformat(),
                "confirmed",
            ),
        )

        connection.commit()

        return {
            "booking_id": booking_id,
            "user_id": user_id,
            "trip_id": trip_id,
            "booked_on": date.today().isoformat(),
            "status": "confirmed",
        }

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def cancel_booking(booking_id):
    """Cancel a booking while retaining its database record."""
    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            UPDATE bookings
            SET status = 'cancelled'
            WHERE booking_id = ?
            """,
            (booking_id,),
        )

        if cursor.rowcount == 0:
            raise ValueError("Booking does not exist.")

        connection.commit()

        return {
            "booking_id": booking_id,
            "status": "cancelled",
        }

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def delete_booking(booking_id):
    """Permanently delete a booking."""
    connection = get_connection()

    try:
        cursor = connection.execute(
            "DELETE FROM bookings WHERE booking_id = ?",
            (booking_id,),
        )

        if cursor.rowcount == 0:
            raise ValueError("Booking does not exist.")

        connection.commit()

        return {
            "booking_id": booking_id,
            "deleted": True,
        }

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()
