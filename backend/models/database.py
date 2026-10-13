import csv
import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "expedia_lite.db"


def get_connection():
    """Open a connection to the Expedia Lite SQLite database."""
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def create_tables(connection):
    """Create the application tables if they do not already exist."""

    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS hotels (
            hotel_id TEXT PRIMARY KEY,
            hotel_name TEXT NOT NULL,
            city TEXT NOT NULL,
            state TEXT NOT NULL,
            nightly_rate_usd REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            display_name TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS trips (
            trip_id TEXT PRIMARY KEY,
            hotel_id TEXT NOT NULL,
            trip_name TEXT NOT NULL,
            check_in TEXT NOT NULL,
            check_out TEXT NOT NULL,
            FOREIGN KEY (hotel_id) REFERENCES hotels(hotel_id)
        );

        CREATE TABLE IF NOT EXISTS bookings (
            booking_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            trip_id TEXT NOT NULL,
            booked_on TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('confirmed', 'cancelled')),
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (trip_id) REFERENCES trips(trip_id)
        );

        CREATE TABLE IF NOT EXISTS app_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """
    )


def read_csv(filename):
    """Read one of the supplied UTF-8-with-BOM CSV files."""
    path = DATA_DIR / filename

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def seed_database(connection):
    """
    Seed the database from the four supplied CSV files only once.

    The app_meta table remembers that seeding has already happened so
    later application restarts do not restore deleted bookings or
    duplicate starter data.
    """

    already_seeded = connection.execute(
        "SELECT value FROM app_meta WHERE key = 'seeded'"
    ).fetchone()

    if already_seeded:
        return

    hotels = read_csv("hotels.csv")
    trips = read_csv("trips.csv")
    users = read_csv("users.csv")
    bookings = read_csv("bookings.csv")

    try:
        connection.executemany(
            """
            INSERT INTO hotels
                (hotel_id, hotel_name, city, state, nightly_rate_usd)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (
                    row["hotel_id"],
                    row["hotel_name"],
                    row["city"],
                    row["state"],
                    float(row["nightly_rate_usd"]),
                )
                for row in hotels
            ],
        )

        connection.executemany(
            """
            INSERT INTO users
                (user_id, display_name)
            VALUES (?, ?)
            """,
            [
                (
                    row["user_id"],
                    row["display_name"],
                )
                for row in users
            ],
        )

        connection.executemany(
            """
            INSERT INTO trips
                (trip_id, hotel_id, trip_name, check_in, check_out)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (
                    row["trip_id"],
                    row["hotel_id"],
                    row["trip_name"],
                    row["check_in"],
                    row["check_out"],
                )
                for row in trips
            ],
        )

        connection.executemany(
            """
            INSERT INTO bookings
                (booking_id, user_id, trip_id, booked_on, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (
                    row["booking_id"],
                    row["user_id"],
                    row["trip_id"],
                    row["booked_on"],
                    row["status"],
                )
                for row in bookings
            ],
        )

        connection.execute(
            "INSERT INTO app_meta (key, value) VALUES ('seeded', 'true')"
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise


def initialize_database():
    """Create the database schema and load starter records once."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    connection = get_connection()

    try:
        create_tables(connection)
        seed_database(connection)
    finally:
        connection.close()


if __name__ == "__main__":
    initialize_database()
    print(f"Database ready: {DB_PATH}")