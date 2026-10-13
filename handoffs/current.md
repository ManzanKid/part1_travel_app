# Current Handoff

## What works

Part 2 is implemented on the `part2-sqlite-crud` feature branch.

The application currently supports:

- Hotel-name search.
- Demo traveler selection.
- Simulated booking creation.
- Booking history.
- Cancelling a booking while keeping the record.
- Deleting a test booking.
- SQLite persistence across browser refreshes.
- SQLite persistence across frontend and backend restarts.

The supplied CSV files are used to seed SQLite once. After seeding, application reads and writes use the database.

## What was checked

Manual browser verification was completed using Demo Traveler 1 (`U001`).

Observed results:

- Searching for `Harbor Lantern Hotel` returned `T001` and `T009`.
- Booking `B007` was created for `T001` and appeared immediately as Confirmed.
- `B007` was cancelled and remained in booking history with a Cancelled status.
- The cancelled status persisted after refreshing the browser.
- The cancelled status persisted after restarting both the frontend and backend.
- `B007` was deleted and remained deleted after refreshing the browser.

Verification screenshots are stored in `docs/screenshots/`.

## Remaining work

Before submission:

- Update `report.md` with the Part 2 implementation and manual verification results.
- Embed the verification screenshots in `report.md`.
- Review the feature branch changes.
- Commit the Part 2 work.
- Merge the feature branch into `main`.
- Run a final combined-app check.
- Push the final Part 2 commit to GitHub.
- Add the exact Part 2 commit hash to `report.md`.

## Next task

Update `report.md`, complete the demo video, and prepare the feature branch for final review and merge.