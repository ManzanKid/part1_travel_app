import csv
import os
import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = Path(os.environ.get("EXPEDIA_LITE_DB_PATH", DATA_DIR / "expedia_lite.db")).expanduser()


def get_connection(db_path=None):
    """Open a connection to the shared app database, optionally at a test path."""
    path = Path(db_path or DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
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

CREATE TABLE IF NOT EXISTS saved_hotels (
    hotel_id TEXT NOT NULL PRIMARY KEY,
    name TEXT,
    address TEXT,
    latitude REAL NOT NULL CHECK (latitude BETWEEN -90 AND 90),
    longitude REAL NOT NULL CHECK (longitude BETWEEN -180 AND 180)
);

CREATE TABLE IF NOT EXISTS demo_hotel_nights (
    hotel_id TEXT NOT NULL,
    stay_date TEXT NOT NULL CHECK (
        stay_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
    ),
    nightly_rate_cents INTEGER NOT NULL DEFAULT 10000
        CHECK (typeof(nightly_rate_cents) = 'integer'
               AND nightly_rate_cents >= 0),
    rooms_available INTEGER NOT NULL DEFAULT 20
        CHECK (typeof(rooms_available) = 'integer'
               AND rooms_available >= 0),
    PRIMARY KEY (hotel_id, stay_date),
    FOREIGN KEY (hotel_id)
        REFERENCES saved_hotels(hotel_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS saved_hotel_locations (
    hotel_id TEXT NOT NULL,
    postcode TEXT NOT NULL,
    locality TEXT,
    country_code TEXT NOT NULL DEFAULT 'us',
    latitude REAL NOT NULL CHECK (latitude BETWEEN -90 AND 90),
    longitude REAL NOT NULL CHECK (longitude BETWEEN -180 AND 180),
    PRIMARY KEY (hotel_id, postcode),
    FOREIGN KEY (hotel_id) REFERENCES saved_hotels(hotel_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS pausepath_sessions (
    session_id TEXT PRIMARY KEY,
    skill_id TEXT NOT NULL CHECK (skill_id IN ('breathing', 'stop')),
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL,
    duration_ms INTEGER NOT NULL CHECK (duration_ms >= 0),
    status TEXT NOT NULL CHECK (status IN ('completed', 'stopped')),
    saved_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pausepath_chat_threads (
    thread_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    skill_id TEXT NOT NULL CHECK (skill_id IN ('breathing', 'stop'))
);

CREATE TABLE IF NOT EXISTS pausepath_chat_messages (
    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (thread_id)
        REFERENCES pausepath_chat_threads(thread_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS pausepath_preferences (
    preference_key TEXT PRIMARY KEY CHECK (preference_key = 'simpler_view'),
    preference_value TEXT NOT NULL CHECK (preference_value IN ('true', 'false')),
    updated_at TEXT NOT NULL
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
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = get_connection()

    try:
        create_tables(connection)
        seed_database(connection)
    finally:
        connection.close()


if __name__ == "__main__":
    initialize_database()
    print(f"Database ready: {DB_PATH}")
