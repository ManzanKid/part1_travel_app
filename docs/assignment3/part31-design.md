# PausePath — Assignment 3.1 Research and Design Notes

**Type:** Early design proposal, before application implementation  
**Scope:** Coursework prototype tested only with fictional scenarios  
**Stack for future implementation:** Vue frontend, FastAPI backend, SQLite history, backend-only optional LLM provider.

## 1. Research basis and limits

The course-supplied research summary is the primary design input. It describes an ongoing study involving **15 patients, 13 clinicians, 15 prototype evaluation sessions, and 150 participant–task combinations**. Its coded mentions describe observed preferences and usability friction, **not clinical effectiveness or the prevalence of each preference in a population**. I am not conducting clinical research for this assignment.

### Requirements → concrete choices

| Finding | Study evidence | Design decision | Verification planned |
|---|---|---|---|
| R1 — Over 90–100 seconds loses attention | 38 mentions; ~60 seconds comfortable | Six 4–6 breath cycles = **60 seconds**; four STOP stages ≈ **60 seconds**; never wait for a model call mid-skill | Measure first instruction to last planned step in browser; list delays and user-selected pauses separately |
| R2 — Crisis access frictionless | 30 mentions across all 15 participants | Persistent, clearly labeled **Crisis information** control and direct external 988 option | Verify link on every view and during simulated model failure |
| R3 — Permission to stop | 39 mentions; all 15 on permission-to-stop task | Always-visible **Stop / Leave**; no scolding, score or forced survey | Leave during every step and on error |
| R4 — User controls journey | 68 mentions; strongest requirement | Two equally visible skill choices; AI suggestion may be ignored; Back and Pause | Select the nonrecommended skill and leave freely |

### Design principles → concrete choices

| Finding | Study evidence | Design decision | Tradeoff |
|---|---|---|---|
| D1 — Progressive contraction | 54 mentions | **Simpler view** toggle makes one action and controls prominent; no distress inference | User must activate it; no automatic detection claim |
| D2 — One atomic skill | 100 mentions across 15 participants | Only a single inhale/exhale or STOP step on screen at a time | Fewer instructions visible simultaneously |
| D3 — Minimize emotional cost | 148 mentions, all participants | No compulsory typing, emotional labels, disclosures, or reflections | Less detail for personalization |
| D4 — Persistent safety | 31 mentions | Crisis information in an always-visible header area, not inside AI messages | Uses scarce screen space intentionally |
| D5 — Personalize without configuration | 49 mentions | **Repeat last skill** appears only after a person opts into saved history; no questionnaire | No personalization until a session is saved |
| D6 — Low-stimulus language | 97 mentions across 15 participants | Muted palette; short plain copy; subtle or disabled motion; no praise/shame | Some people may prefer more animation, so provide an option |

## 2. Skill scope — intentionally narrow

**Option A: 4–6 paced breathing.** The view alternates **Inhale — 4** and **Exhale — 6**, with a visible count, text cue and optional quiet visual expansion/contraction. Repeat **six cycles (60 seconds)**. Start, Pause/Resume, Stop/Leave and Crisis information remain reachable. For reduced motion, the text/count remains sufficient; the animation is not required to use the skill. The UI does not say a user must breathe at a fixed pace if uncomfortable; user can stop or switch.

**Option B: STOP.** Exactly four instructions, presented one at a time and in order: **Stop**; **Take a step back**; **Observe what is happening internally and externally**; **Proceed mindfully**. The reference pace is four ~15-second steps (≈60 seconds), with user-controlled Pause/Stop/Back and optional early Next. The user need not type anything or respond to prompts. If steps advance automatically, evaluate whether it feels rushed and consider making Next-only the default.

**Why not 5-4-3-2-1 or cognitive reframe now?** Grounding requires attention to five sensory categories; reframe asks the user to articulate a distressing thought and compare evidence. Both are valid study skills, but may ask for more attention, input or disclosure than the two selected skills. This is a design scope decision, not a clinical judgment.

**Timing specification.** Count the exercise starting with the *first presented skill instruction*, ending after its last planned step. Breathing: 6 × (4 + 6) = 60 seconds, plus a few seconds to show completion; target **under 70 seconds** in normal foreground operation. STOP: 4 × 15 seconds = 60 seconds, plus transitions; target **under 70 seconds**. No model call is made during the timed sequence. Report page entry/selection separately; exclude only genuinely user-chosen pauses and time used for crisis information. Do not forcibly end a voluntary pause at 90 seconds. Background-tab timer suspension becomes a paused state. In Parts 3.2/3.3 the measured elapsed durations must replace these *design estimates*.

## 3. Screen behavior and copy

1. **Welcome / Choose:** "Choose one short activity." Two prominent choices: **4–6 breathing (~60 s)** and **STOP (~60 s)**. Optional: "Help me choose" and "Repeat last" if history was saved. Persistent Crisis information, Simpler view, and neutral coursework disclaimer.
2. **Optional model suggestion:** Person may enter a *fictional* phrase of up to ~160 characters. Backend requests a structured `skill_id` of `breathing` or `stop`, plus one neutral reason. Only whitelisted skill IDs accepted. App still shows both options. No diagnoses or therapeutic instructions.
3. **One-step exercise:** One instruction, progress indicator, **Pause**, **Stop / Leave**, **Crisis information**. Avoid long paragraphs and unsolicited model messages.
4. **Finish:** "That step is complete. You may leave, repeat, or choose another." Optional **Save to history**; no rating required. Stop exits directly, without completion nagging.
5. **History:** Only saved practice sessions are shown (skill, date, duration, completed/stopped when user opted in). Allow deletion. Optional saved fictional model exchanges are labeled as prototype data.
6. **Crisis information:** A static route independent of the model, available even offline where the UI itself is loaded. U.S. options: call/text 988 or visit https://988lifeline.org/get-help/; for immediate danger call 911. Wording clearly states the prototype does not monitor or provide emergency help. Do not claim this prototype replaces a service.

## 4. Interaction and safety decisions

- **No clinical claims.** The app is not diagnosis, therapy, crisis counseling, medical monitoring or a service for real users.
- **Fictional evaluation only.** All screenshots, recordings and model tests use fictional scenarios. No user in distress is recruited.
- **Independent crisis access.** A normal clickable button/link in the Vue layout opens a static help view; it never relies on an LLM decision, classifier, database operation or network request to appear.
- **Crisis-like input.** A conservative local rule may show a static notice for obvious *fictional* phrases of imminent harm. It is incomplete and may miss or overflag language. It never controls access to the help view. Model generation can be bypassed for such test inputs. No claims about detecting a person's risk.
- **Graceful LLM failure.** If model times out, reaches quota or returns an invalid skill ID, show: "Suggestions aren't available. You can choose either activity." Both static skills and crisis information continue to work.
- **User permission.** Stop/Leave never requires explanation; Pause never times out into forced completion; saving history is optional; review and delete are available.
- **Accessibility.** Keyboard use, visible focus, logical headings, sufficient contrast, reduced-motion fallback, `aria-live` for short step changes without excessive announcements, buttons large enough to select, and no audio-only instructions.
- **No health-data claims.** Stored practice records are not measurements of improvement, diagnosis or treatment. Show retention/deletion controls in the actual implementation; no real personal data should be used in coursework tests.

## 5. LLM boundaries, architecture and data

**Architecture:** Vue owns displayed navigation, timing cues and controls → FastAPI owns business rules, optional model requests and SQLite → SQLite stores opt-in data. Secrets and model calls remain exclusively in the backend. Adapt the proven Vue/FastAPI/SQLite patterns from Expedia Lite, but keep this new feature isolated from the travel app and hotel data. No embedding/vector store is required by the proposed use.

**Allowed model function:** Given a *fictional* short situation and the two known skill descriptions, choose `breathing` or `stop` with a short, nonjudgmental reason. With explicit consent and saved history, another optional question can request a factual recap ("You last practiced STOP") from limited stored records. Both outputs are checked by backend rules and cannot replace fixed skill scripts.

**Prohibited model function:** Generate a new breathing sequence or therapy technique; label mental disorders; assess risk reliably; decide whether crisis help is shown; change session data; auto-complete an exercise; claim to monitor someone or provide medical advice.

**Proposed tables (not yet implemented):**

| Table | Useful fields | Why retain it |
|---|---|---|
| `practice_sessions` | `id`, `skill_code`, `started_at`, `finished_at`, `duration_ms`, `status`, `saved_at` | Review previous **opt-in** sessions and measure planned vs actual duration |
| `chat_threads` | `id`, `started_at`, optional `practice_session_id` | Group an opt-in fictional dialogue |
| `chat_messages` | `id`, `thread_id`, `role`, `content`, `created_at` | Let the fictional conversational feature keep context when saved |
| `preferences` | `last_skill_code`, `simpler_view` | Offer Repeat last or a previously selected display setting with minimal setup |

**Retention:** Do not persist the optional situation text or messages by default. During normal unsaved use, hold transient content only as needed for the request. Provide explicit **Save to history** and **Delete history**. For later parts, document how an opted-in chat log connects to its saved session and verify restart persistence. Use generated fictional examples in tests and demonstrations.

## 6. Alternatives, tradeoffs and rejected approaches

- **Chat-first vs skill-first:** A free-form AI counseling screen might invite typing and disclosure. I rejected that as the initial experience (D2/D3). Two skill choices are available without chat; AI remains optional.
- **Automatic distress detection vs explicit simpler view:** The study does not establish a dependable distress signal (D1). I selected a user control instead, avoiding unsupported claims but requiring one extra tap.
- **Always-on logging vs consent-based history:** History can support D5 but may increase effort and privacy cost under D3/R3. I selected opt-in saving, accepting weaker personalization before the first saved session.
- **Rich animation vs quiet pacing:** Motion may help breathing but be demanding for some users (D6). Use readable text/count as baseline, with optional subtle animation that respects reduced-motion preferences.

## 7. Early verification plan (future work)

These are **planned test cases**, not passed tests:

1. Fictional user chooses breathing and finishes six cycles; measured intended duration stays under 90 seconds.
2. Fictional user chooses STOP, sees every step in order, and can leave from step 2 without a warning.
3. Model times out; direct skill selection and crisis information still work.
4. Simpler view enabled; only primary instruction and persistent controls remain prominent.
5. Optional model suggests STOP but user chooses breathing; application follows user's choice.
6. Session is explicitly saved; it appears in SQLite and in History after restart; deleting removes it.
7. A fictional crisis phrase shows appropriate static crisis-information wording without any claim of real risk assessment.

For 3.3 expand to **at least fifteen fictional scenarios** and **three cross-case invariants**: (a) persistent crisis help never disappears, (b) exit is always available without penalty, and (c) skill steps are fixed, ordered and unaffected by model output. Record expected/observed results and separate mocked from live model checks.

## 8. Sources

- Course-provided **Assignment 3 — Mental Health Skills Application**, Section 3 study summary and Section 4–7 requirements (primary research foundation; provided with assignment).
- [988 Lifeline — Get Help](https://988lifeline.org/get-help/) (public crisis information source; not an endorsement of the coursework prototype).

No independent clinical evaluation or claims about efficacy are made. Any external UI examples or provider documentation used in later milestones will be recorded separately.
