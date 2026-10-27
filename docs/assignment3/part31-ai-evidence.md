# Assignment 3.1 — AI-use evidence and design revisions

**Date prepared:** October 27, 2026

**Tools used for Assignment 3.1:** OpenAI ChatGPT, model GPT-6, for interpreting the course brief and drafting Part 3.1 design/report/wireframe.

**Coding agent used for Assignment 3.2:** OpenAI Codex, running on the GPT-6 model family exposed by the agent environment; a more specific model/version identifier was not available in this session. Codex inspected the existing app and Part 3.1 design, implemented the PausePath Vue view, FastAPI routes, SQLite tables/controller, deterministic tests, and updated project documentation.

**LLM in the application:** The optional recommendation is configured for `nvidia/nemotron-3.5-lightning:free` in the current environment. No live OpenRouter calls were made during Assignment 3.2 implementation or automated testing. Automated model tests use mocked responses. The backend rejects non-`:free` model IDs for PausePath recommendations.

## Evidence log

| Input or design discussion | Artifact / decision | Check status |
|---|---|---|
| Student provided *Assignment 3 — Mental Health Skills Application* and asked to complete Part 3.1 | Read R1–R4 / D1–D6 and built design notes, report, flow and early mockup | Compared planning content to the supplied brief, no prototype execution |
| Early alternative: make an open-ended chatbot the default screen | **Revised** to an optional, constrained suggestion flow with two direct skill buttons | Design rationale tied to D2, D3 and R4; not user-tested |
| Early alternative: infer rising distress and simplify automatically | **Rejected**; user-initiated Simpler view because D1 provides no reliable detection rule | Design rationale; not a clinical safety detector |
| Early alternative: save every chat/session automatically | **Revised** to optional saving with deletion in History | Design rationale balancing D5 and D3/R3; implementation remains future work |
| Assignment 3.2 implementation: phrase check initially missed the fictional wording “wants to die” | **Corrected** the bounded phrase rule to match “want” and “wants”; added deterministic frontend and backend assertions | Phrase matching remains incomplete and is not represented as risk detection |
| Assignment 3.2 frontend checks | The Anaconda Node/npm wrapper initially failed with `dyld: Symbol not found: _sqlite3changeset_apply`; a sibling SQLite 3.53.4 library was loaded for direct Node processes | No packages or installed files were changed. Four timing-rule tests, all Vue SFC compiler checks, and a Vite production build then passed through direct Node CLI invocation. Standard npm wrappers still need a compatible runtime or equivalent local setup. |

## Known limits

The Assignment 3.1 report and mockup remain planning artifacts; they contain no real user testing or clinical validation. Assignment 3.2 automated checks use temporary databases and mocked model responses. The browser verification sheet is prepared, but its observed-results cells remain blank until the student personally verifies the application. The exercise durations are implemented from the planned timing rules but have not been manually measured in a browser. All scenarios in tests are fictional, and no credentials or private material appear in this evidence.

This evidence is summarized in the repository's root `AI-USE.md`. Before final Assignment 3 submission, add any later tools, exact model identifiers that become available, browser/database observations, and future implementation changes.
