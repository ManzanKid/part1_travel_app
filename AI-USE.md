# AI use disclosure

## Assignment 3.1

OpenAI ChatGPT (GPT-6) was used to interpret the course brief and prepare the early design, report, and wireframe. These were planning artifacts, not results from user or clinical testing.

## Assignment 3.2

OpenAI Codex was used as the coding agent to inspect the Expedia Lite application and Assignment 3.1 materials, implement the PausePath interface/backend/persistence/tests, and update project documentation. The agent environment identified the model family as GPT-6; it did not expose a more specific model or version identifier.

No live OpenRouter calls were made during Assignment 3.2 implementation or automated testing. Backend recommendation tests use mocked outputs. The optional application recommendation is configured for `nvidia/nemotron-3.5-lightning:free` in the current environment, runs only after a user submits a fictional scenario, and accepts only the `breathing` or `stop` skill ID. The backend rejects configured model IDs without the `:free` suffix. No paid model fallback is configured.

All automated PausePath scenarios are fictional. No real personal scenario, API key, or private credential was included in AI-use evidence. Browser behavior and restart persistence remain for the student to verify manually using [the Assignment 3.2 verification sheet](docs/assignment3/part32-verification.md).

See [the detailed Assignment 3.1 AI-use evidence and design revisions](docs/assignment3/part31-ai-evidence.md).
