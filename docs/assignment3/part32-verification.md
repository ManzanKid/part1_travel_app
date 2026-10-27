# Assignment 3.2 — PausePath verification

**Branch:** `assignment3-part2`  
**Purpose:** Expected behavior for the student's manual browser and persistence verification.  
**Safety scope:** Fictional scenarios only. PausePath is not therapy, diagnosis, crisis monitoring, or an emergency service.

The observed-results column below is intentionally empty. Fill it only after personally checking the running application and database. Automated results are recorded separately after that table.

## Launch

Start FastAPI in one terminal:

```bash
cd backend
source .venv/bin/activate
uvicorn main:app --reload --port 8000
```

Start Vue in a second terminal:

```bash
cd frontend
npm run dev
```

In this workspace, the Anaconda npm wrapper fails during Node startup. Use its direct Vite equivalent instead:

```bash
cd frontend
env DYLD_INSERT_LIBRARIES=/opt/anaconda3/lib/libsqlite3.3.53.4.dylib DYLD_FORCE_FLAT_NAMESPACE=1 /opt/anaconda3/bin/node node_modules/vite/bin/vite.js --host 127.0.0.1
```

Open `http://localhost:5173/`, then select **PausePath** in the application switcher. Use only fictional inputs. The optional recommendation may contact the configured free OpenRouter model after the user submits a scenario; no live model calls were made during implementation or automated checks.

## Manual expected-versus-observed checks

| Check | Expected result | Observed result (student to fill) |
|---|---|---|
| App separation | Expedia Lite remains available in its own view; PausePath has its own screens and navigation. | |
| Prototype disclaimer | PausePath says fictional coursework prototype and explains it is not therapy, diagnosis, monitoring, or a real support service. | |
| Direct skill choice | Both 4–6 breathing and STOP can be started without typing or requesting a model suggestion. | |
| 4–6 breathing timing | Six inhale/exhale cycles appear one instruction at a time: inhale 4 seconds, exhale 6 seconds. Intended active duration is 60 seconds and below 90 seconds. | |
| Breathing pause and resume | Pause freezes the countdown and excludes paused time from the saved active duration; Resume continues from the current cue. | |
| Inactive tab | Switching away from the browser tab automatically pauses the exercise. Returning does not auto-resume it. | |
| STOP order and timing | The four single-step instructions appear in order: Stop; Take a step back; Observe what is happening internally and externally; Proceed mindfully. Each targets about 15 seconds; intended total is about 60 seconds. | |
| STOP pause | A paused STOP step does not advance automatically. Resume is required before its timer continues. | |
| Stop / Leave | Stop / Leave is available on every PausePath screen. Leaving an active exercise produces an early-exit completion state without scolding or a required explanation. | |
| Crisis information availability | The Crisis information control remains visible on home, exercise, paused, completion, history, suggestion-loading, and suggestion-error screens. It opens without an API or model request. | |
| Static U.S. crisis information | The screen lists call/text 988, 911 for immediate emergencies, and says PausePath does not monitor users or provide emergency assistance. | |
| Fictional crisis-like phrase | An obvious fictional crisis phrase bypasses generated suggestions and opens the static crisis-information screen. The wording does not claim reliable detection or risk assessment. | |
| Suggestion boundary | A successful optional suggestion is only `breathing` or `stop`; it never generates instructions or starts an exercise automatically. The user can choose the other skill. | |
| Suggestion failure | With the optional model unavailable or returning invalid output, a simple error appears; direct skill choices and Crisis information remain usable. | |
| Session consent | Finishing or leaving does not save automatically. Only clicking **Save this session to history** creates a session record. | |
| Session fields and restart | A saved session shows the skill, timestamps, active duration, and completed/stopped status in history after page refresh and backend restart. Pauses/setup time are excluded from duration. | |
| Session deletion | Deleting one saved session removes it from history and leaves unrelated Expedia Lite records intact. | |
| Conversation consent | With consent unchecked, an AI exchange is not stored. With **Save this fictional exchange to history** checked before requesting the suggestion, the fictional scenario and bounded recommendation appear in history. | |
| Conversation restart and deletion | A consented fictional exchange remains visible after backend restart and can be deleted individually or with all saved PausePath history. | |
| Repeat last saved skill | After a session is saved, the home screen offers the last saved skill; it still starts only after the user selects it. | |
| Simpler view | The user can turn Simpler view on/off; it changes the display emphasis and the setting remains after refresh when persistence is available. | |
| Expedia regression | Hotel search, map selection, local save/remove, booking creation, history, cancellation, and deletion remain available in the Expedia Lite view. | |

## Automated checks run

| Check | Result |
|---|---|
| Backend `unittest` suite with `EXPEDIA_LITE_DB_PATH` pointed at a temporary database | Passed: 57 tests |
| Frontend deterministic Node timing-rule tests | Passed: 4 tests, using the installed Node binary directly with a temporary SQLite library environment override |
| Vue SFC script, template, and scoped-style compiler checks for App, PausePath, HotelDiscovery, and HotelChatbot | Passed |
| Standard `npm test` and `npm run build` wrappers | Could not start: their `/usr/bin/env node` child lost the temporary library override and exited with code 134 because dyld could not resolve `_sqlite3changeset_apply` |
| Vite production build through its installed CLI with a temporary outDir | Passed: Vite 8.3.5 transformed 21 modules and built JS/CSS/HTML into `/private/tmp/pausepath-vite-build` |
| Live OpenRouter request | Not made |

## Implementation notes and corrections

- A deterministic crisis-phrase check initially missed the inflected phrase “wants to die.” The frontend and backend checks were corrected to match both “want” and “wants”; this bounded phrase check is still incomplete and is not a risk detector.
- The installed local Node binary initially failed with `dyld: Symbol not found: _sqlite3changeset_apply` from the Anaconda `libnode`/SQLite linkage. A sibling SQLite 3.53.4 library in the same Anaconda installation exports the missing symbol. Loading it for direct Node processes (without changing installed files or packages) allowed the timing-rule test and Vite build to pass. The standard `npm` script shell still drops that environment override, so on this host use the direct Node commands recorded in the handoff. A normal compatible Node/npm installation can use the standard commands from README.md.
