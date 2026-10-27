# Assignment 3.2 — Working Application and Safety

**Project:** PausePath  
**Repository:** https://github.com/ManzanKid/part1_travel_app  
**Branch:** `assignment3-part2`  
**Commit:** Add final commit hash  
**Demo:** https://drive.google.com/file/d/10QLAyARm4mumzjwRjuboT2l5Cyjjpb8H/view?usp=sharing

## What I Built

For Part 3.2, I turned my PausePath design into a working application using Vue, FastAPI, and SQLite. I kept it separate from Expedia Lite so the original hotel features still work.

The application includes two exercises: 4–6 paced breathing and STOP. Breathing uses six cycles of four seconds inhaling and six seconds exhaling, for a planned total of 60 seconds. STOP walks through its four steps one at a time. Both exercises allow users to pause or leave whenever they want.

I also added an optional AI recommendation feature using OpenRouter. The model can suggest breathing or STOP based on a fictional situation, but it cannot create new exercises or control the instructions.

## Safety and Database

One thing I focused on was making sure the exercises and Crisis information did not depend on the AI. The application has a separate Crisis information screen with 988 and 911 information. It also explains that PausePath is only a class project and not a real mental health service.

I used SQLite to support optional saved exercise sessions, conversation history, and preferences. Users can review and delete their saved information. Nothing needs to be saved just to complete an exercise.

## Testing and My Observations

Codex ran 57 backend tests and four frontend timing tests, which passed. The Vite build also passed using a workaround because my local Anaconda Node installation caused problems with the usual npm commands.

I manually opened the application and tested its features. I also recorded a demonstration of the exercises and AI functionality.

I specifically tested what happened when the AI request failed. I stopped the backend and tried using the recommendation feature. The request failed as expected. This was an important test because I wanted the basic exercises and Crisis information to remain available even when the AI was not working.

The exercise timing is designed to stay under 90 seconds. I still need to include my exact manually observed duration and confirm the restart-persistence results in my [verification notes](docs/assignment3/part32-verification.md), rather than relying only on automated tests.

## Problems and Next Steps

One issue Codex found was that the fictional crisis phrase "wants to die" was not initially recognized. The matching logic was corrected, although keyword matching is still limited and cannot reliably detect a crisis.

For Part 3.3, I want to test more fictional scenarios, improve the interface, and make sure saved history and personalization work consistently. The application is still a coursework prototype and has not been clinically evaluated.

## AI Use

I used ChatGPT (GPT-6) for planning and documentation and Codex in VS Code to help implement and test the application. OpenRouter provides the optional skill recommendations. Additional information is in [AI-USE.md](AI-USE.md).

## Demonstration

[Assignment 3.2 — PausePath Recording](https://drive.google.com/file/d/10QLAyARm4mumzjwRjuboT2l5Cyjjpb8H/view?usp=sharing)