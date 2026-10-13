# Selected Part 2 Prompts

These are selected prompts used while developing Expedia Lite Part 2.

## SQLite setup

Implement Part 2 using SQLite. Use the supplied hotels, trips, users, and bookings CSV files to seed the database once. After seeding, all application reads and writes should use SQLite.

## MVC structure

Organize the backend using an MVC-style structure. Keep database setup and schema management in the model layer, database CRUD operations in a controller, and use the Vue frontend as the View.

## Booking CRUD

Add frontend and backend functionality that allows a demo traveler to create a booking, view booking history, cancel a booking while retaining the record, and delete a test booking.

## Persistence

Make sure booking changes persist after refreshing the browser and after restarting both the frontend and backend. Restarting the application should not duplicate or reload the starter data.

## UI

Improve the Vue interface so users can select a demo traveler, search for hotel stays, book a trip, view booking history, cancel bookings, and delete test bookings.