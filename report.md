# Expedia Lite — Part 1

## Repository and commit
Repository URL: Repository URL: https://github.com/ManzanKid/part1_travel_app

Exact Part 1 commit: 3e510471bb23be3891b715117370ff21b112c4cd

## Implementation
The Part 1 application uses Vue for the frontend and FastAPI/Python for the backend. The frontend provides a hotel-name search input and Search button. It sends the search term to the FastAPI `/api/search` endpoint. The backend reads the supplied `hotels.csv` and `trips.csv` files using UTF-8-with-BOM-safe CSV loading, matches hotel names case-insensitively, and connects hotel and trip records using `hotel_id`. The API returns the matching stays as JSON. The Vue frontend displays the results in a plain table with the hotel name, location, nightly rate, trip ID, stay name, check-in date, and check-out date. When there are no matches, the frontend displays a clear no-results message.

## Verification
Action: Search for `Harbor Lantern Hotel`.

Expected result: Two matching stays appear for Harbor Lantern Hotel: `T001` — Boston Harbor Weekend (2026-09-18 to 2026-09-20) and `T009` — Boston Autumn Weekend (2026-10-02 to 2026-10-04).

Observed result: Two matching stays were displayed successfully: `T001` — Boston Harbor Weekend and `T009` — Boston Autumn Weekend.

Action: Search for `zzzz-no-hotel`.

Expected result: No table rows are shown and a clear no-results message appears.

Observed result: The application displayed: `No results found for "zzzz-no-hotel".`

Screenshot(s): [PASTE REPOSITORY LINK(S) TO SCREENSHOTS, IF YOU TOOK THEM]

## Project context and next steps
README: `README.md`

Project-specific agent instructions: `AGENTS.md`

Design note: `docs/design.md`

Selected prompts: `prompts/`

Current handoff: `handoffs/current.md`

Remaining limitation / next task: Complete the required browser verification, add any screenshot links, commit and push the reviewed Part 1 work, and paste the repository URL and exact Part 1 commit above. Part 2 (SQLite CRUD) is intentionally not implemented.
