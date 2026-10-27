# Expedia Lite — Assignment 2 Part 1 Report

## Repository and Commit

**Repository URL:** https://github.com/ManzanKid/part1_travel_app

**Branch:** `assignment2-part1`

**Exact Assignment 2 Part 1 commit:** e50b16ad9dbacc8e3437e7fa21c63b73ca411872

**Verification date:** October 26, 2026

## 1. Project Overview

For Assignment 2 Part 1, I expanded my Expedia Lite application by adding a feature that lets users search for real hotels near a five-digit U.S. ZIP code.

The application uses Geoapify to find the location of the ZIP code and retrieve hotels within a five-kilometer radius. The results appear in a list alongside an interactive Leaflet map.

Users can select hotels from either the list or the map, and the selected hotel updates in both places. I also added input validation, loading messages, and error handling for unsuccessful searches.

The original hotel search and simulated SQLite booking functionality from Assignment 1 remain available.

## 2. Research and Design

Before implementing the feature, I researched Geoapify, Leaflet, and the Google Hotels interface.

My research document is available here:

[Assignment 2 Part 1 Research and Design](docs/assignment2-part1-research.md)

### Geoapify Places API

Source: https://apidocs.geoapify.com/docs/places/

I chose Geoapify because it provides actual hotel locations, coordinates, and addresses. It also supports geographic filtering, which allowed me to request hotels within 5,000 meters of a ZIP code.

I decided to make these requests through my FastAPI backend so that the Geoapify API key would not be exposed in the frontend.

### Leaflet

Source: https://leafletjs.com/examples/quick-start/

I used Leaflet because it supports interactive maps, markers, zooming, and user interactions.

My design connects each hotel in the results list with its corresponding map marker, allowing users to navigate the results using either interface.

### Google Hotels

Source: https://www.google.com/travel/hotels

I looked at Google Hotels as a design reference. I liked how it displays hotel results alongside a map, making it easier to compare locations. Its reviews, photos, and information about nearby attractions were also useful design ideas.

For this assignment, I focused on implementing the hotel list and map interaction rather than attempting to recreate all of Google Hotels' features.

## 3. Early Mockup

I created an early mockup before implementing the complete hotel discovery interface.

![Assignment 2 Part 1 Early Mockup](docs/assignment2-part1-mockup.png)

The mockup showed a ZIP code input near the top, hotel results on the left, and an interactive map on the right.

My completed implementation follows this general layout. I also added distances from the ZIP code center, a visible five-kilometer search circle, and visual highlighting for the selected hotel.

The example information in the mockup was illustrative. The completed application uses real Geoapify results rather than inventing hotel data.

## 4. Implementation

### Backend

I continued using Python and FastAPI for the backend.

The main files added or modified were:

- `backend/config.py` — Loads the Geoapify API key from the local `.env` file.
- `backend/controllers/geoapify_controller.py` — Validates ZIP codes and retrieves their coordinates using Geoapify.
- `backend/controllers/hotel_discovery_controller.py` — Retrieves nearby hotels from Geoapify Places and processes the results.
- `backend/main.py` — Provides the API routes for the frontend.
- `backend/tests/` — Contains automated tests for geocoding, hotel discovery, and API responses.

The main hotel discovery endpoint is:

`GET /api/discovery/hotels?postcode=16802`

The backend first resolves the ZIP code and verifies that Geoapify returned the requested U.S. ZIP. It then requests hotels within 5,000 meters of the resulting coordinates.

I also added checks for invalid coordinates, duplicate hotels, and locations outside the requested radius.

### Frontend

The frontend uses Vue and Leaflet.

The new `frontend/src/components/HotelDiscovery.vue` component allows users to enter a ZIP code, submit a search, view nearby hotels, and explore their locations on the map.

Selecting a hotel from the list changes the selected marker on the map. Clicking a map marker also updates the selection in the hotel list.

The map shows a circle representing the five-kilometer search radius.

I also implemented different messages for invalid ZIP codes, unresolved ZIP codes, empty results, and provider failures.

### API Key Security

The Geoapify API key is stored in a local `.env` file and is loaded by the FastAPI backend.

I confirmed that Git ignores `.env`, so the API key is not included in the repository.

## 5. Running the Application

The application requires Python, Node.js, and a Geoapify API key.

First, create a `.env` file in the project root containing:

`GEOAPIFY_API_KEY=YOUR_API_KEY`

Start the backend from the `backend` directory:

```bash
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Start the frontend from the `frontend` directory in another terminal:

```bash
npm install
npm run dev
```

Open the application at:

http://localhost:5173/

The Geoapify API key must be configured for live hotel discovery to work.

## 6. Verification and Testing

I tested the hotel discovery feature on October 26, 2026, using the running application and backend tests.

### Live Hotel Search

**Action:** Enter ZIP code `16802` and click Find Hotels.

**Expected result:** The application resolves the ZIP code, retrieves hotels within five kilometers, and displays them in the results list and on the Leaflet map.

**Observed result:** The application resolved ZIP `16802` to State College, Pennsylvania, and returned **21 hotel results**. The hotel list displayed names, addresses, and distances, while the map displayed their markers and the five-kilometer radius.

Examples of returned hotels included Scholar Hotel State College, Hotel State College, Nittany Lion Inn, and Hyatt Place State College.

![Live hotel discovery results for ZIP 16802](docs/screenshots/assignment2-part1-live-results.png)

The number of hotels may change because the results come from a live API.

### Hotel List and Map Synchronization

**Action:** Select a hotel from the results list.

**Expected result:** The corresponding marker becomes selected on the map.

**Observed result:** Selecting a hotel from the list updated the selected map marker.

**Action:** Select a different hotel marker on the map.

**Expected result:** The corresponding hotel becomes selected in the list.

**Observed result:** Clicking a map marker updated the hotel selection in the list.

### Invalid ZIP Code

**Action:** Enter `123`.

**Expected result:** The application rejects the input and displays an error explaining that a five-digit ZIP code is required.

**Observed result:** The application displayed the validation error instead of performing the hotel search.

### Leading-Zero ZIP Code

**Action:** Enter ZIP code `02108`.

**Expected result:** The application preserves the leading zero and searches for the correct ZIP code.

**Observed result:** The leading zero was preserved, and the application processed the ZIP code correctly.

### Unresolved ZIP Code

**Action:** Test a ZIP code that cannot be resolved.

**Expected result:** The application displays a not-found message rather than showing incorrect hotel results.

**Observed result:** The application handled the unresolved ZIP code and displayed the appropriate error state.

### No Nearby Hotels

**Action:** Test a valid response containing no hotel results.

**Expected result:** The application displays a clear message indicating that no nearby hotels were found.

**Observed result:** The empty-results state worked during controlled testing.

### Geoapify Service Failure

**Action:** Test the application with a simulated provider failure.

**Expected result:** The application displays a service error instead of incorrectly reporting that no hotels exist.

**Observed result:** The application displayed the service-failure message during controlled testing.

### Original Hotel Search

**Action:** Search for `Harbor Lantern Hotel` using the original hotel search.

**Expected result:** The existing sample-data hotel search continues working.

**Observed result:** The original search functionality still worked after the new hotel discovery feature was added.

### Automated Backend Tests

I ran **22 backend tests**, and all passed.

These tests covered ZIP code validation, exact ZIP matching, leading zeros, geocoding responses, hotel discovery, radius filtering, duplicate results, missing hotel data, and API error handling.

Some tests used mocked responses to verify failure conditions without depending on the live Geoapify service.

### Frontend Production Build

**Action:** Run `npm run build` from the frontend directory.

**Expected result:** Vite compiles the frontend without build errors.

**Observed result:** The build completed successfully using Vite 8.3.5, transforming 16 modules in 129 milliseconds.

Vite displayed a configuration warning about future native configuration loading, but it did not prevent the build.

## 7. Demonstration Video

I recorded a demonstration showing the hotel discovery feature and its interactions.

**Video:** [Assignment 2 Part 1 — Hotel Discovery Demonstration](https://drive.google.com/file/d/1lTacqJzZnFjfLIifkLg4RHHcVb7d7zxm/view?usp=sharing)

The demonstration covers searching for nearby hotels, viewing the results and map, synchronized hotel selection, and input handling.

## 8. AI Use and Development Process

I used OpenAI ChatGPT (GPT-6) to help plan, implement, test, and troubleshoot parts of this assignment. I also used AI image generation to create the early interface mockup.

Representative requests I made during development included:

- Helping create a FastAPI endpoint that uses Geoapify to resolve a U.S. ZIP code.
- Expanding the ZIP lookup to retrieve hotels within five kilometers.
- Developing tests for valid inputs, invalid ZIP codes, API errors, and hotel discovery.
- Building a Vue component with a Leaflet map and synchronized hotel selection.
- Troubleshooting frontend dependencies and verifying the production build.

An important revision occurred after I implemented the initial Geoapify demonstration. That version only looked up the fixed ZIP code `16802`. Although it confirmed that my API key and backend request were working, it did not provide a complete user-controlled hotel search.

I expanded the implementation to accept any valid five-digit U.S. ZIP code, retrieve real nearby hotels, and display the results on the interactive map.

I also encountered frontend dependency audit warnings. I updated the compatible dependencies, checked the application again, and successfully completed the production build.

I verified the generated implementation by running the backend tests, examining actual Geoapify results, and using the application in the browser. I did not rely only on the generated code or descriptions of expected behavior.

## 9. Limitations and Conclusion

The live hotel discovery feature depends on Geoapify and an active internet connection. Hotel results can change, and the API request uses a result limit, so the application may not display every hotel in a very densely populated area.

The live discovery results include hotel information and locations, but they do not provide verified room availability, live pricing, or actual reservations.

Those features are separate from the simulated booking system implemented in Assignment 1.

Overall, I completed the Assignment 2 Part 1 hotel discovery feature. Users can enter a ZIP code, retrieve nearby real hotels within five kilometers, and interact with the results through a synchronized list and Leaflet map.

The feature was verified through live browser testing, automated backend tests, and a successful frontend production build.