from datetime import date

from models.database import get_connection


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