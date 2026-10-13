# Expedia Lite Design Note

## Frontend

The frontend is built with Vue and acts as the View in the application's MVC-style structure.

It allows the user to:

- Select a demo traveler.
- Search for hotel stays by hotel name.
- View matching trips.
- Create a simulated booking.
- View booking history.
- Cancel a booking while keeping the record.
- Delete a test booking.

The frontend sends HTTP requests to the FastAPI backend and does not access SQLite directly.

## FastAPI

`backend/main.py` provides the API routes between the Vue frontend and the backend controller.

The API supports:

- Hotel search.
- Loading demo travelers.
- Reading booking history.
- Creating bookings.
- Cancelling bookings.
- Deleting bookings.

FastAPI validates incoming requests and passes database work to the controller layer.

## Backend and SQLite

`backend/models/database.py` manages the SQLite database, schema, and initial seed data.

The four supplied CSV files are used only to seed the database the first time it is created:

- `hotels.csv`
- `trips.csv`
- `users.csv`
- `bookings.csv`

After seeding, the application reads and writes SQLite data so changes persist across browser refreshes and application restarts.

`backend/controllers/database_controller.py` performs the application database operations, including:

- Searching hotel stays.
- Reading users and booking history.
- Creating bookings with unique IDs.
- Updating a booking status to `cancelled`.
- Deleting a booking.

## MVC Responsibilities

- Model: SQLite database schema and stored data.
- View: Vue frontend.
- Controller: Database controller functions that perform search and CRUD operations.
- FastAPI routes connect the View to the Controller.

## Persistence

The SQLite database is stored locally at:

`backend/data/expedia_lite.db`

The database file is excluded from Git. The original CSV files remain in the repository as starter data.