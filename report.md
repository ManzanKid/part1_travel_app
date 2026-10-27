# Assignment 3.1 — Research and Design

**Project:** PausePath  
**Repository:** https://github.com/ManzanKid/part1_travel_app  
**Branch:** `assignment3-part1`  
**Design documents commit:** `a9b00d0491b7a7d711d294cfc40c68df0672157e`  
**Earlier report commit:** `51e17ebec21d6aecc4d137c8a16ec5dba0aa1488`  
**Current milestone:** Design only; the Assignment 3 app has not been built yet.

## My idea

For Assignment 3, I want to make a simple app called **PausePath**. The idea is to give someone a short exercise they can follow without having to type a lot or explain how they feel. This is a class prototype, not a therapy app, and I would only test it using fictional situations.

I decided to start with **4–6 breathing** and **STOP** instead of trying to include all four skills from the assignment. Breathing is straightforward to guide with a timer: inhale for four counts and exhale for six, repeated six times for a total of 60 seconds. STOP has four steps: Stop, Take a step back, Observe what is happening internally and externally, and Proceed mindfully. I am planning around 15 seconds per step, although I still need to see whether that feels too fast. Both exercises should take less than 90 seconds at the intended pace, not counting time someone chooses to pause.

I picked these two because neither requires the person to write down upsetting thoughts. The cognitive reframe could be useful, but asking someone to enter a thought and think through evidence seems like more work for a first version. I would rather get a small experience working properly before adding more options.

## How I used the research

The study summary in our assignment describes feedback from 15 patients, 13 clinicians, and 15 prototype evaluation sessions. I used its findings to decide what should actually appear on the screen. The mention counts help explain the design priorities; they do **not** prove that the app or exercises are clinically effective.

The first thing that stood out to me was how often participants wanted to avoid extra effort. **D3** had 148 mentions about minimizing emotional cost, and **D2** had 100 mentions about doing one action at a time. That is why I do not want the main screen to look like a long chatbot conversation. The user sees two skill choices, and once an exercise starts, the screen shows one instruction at a time. There is no required journal entry, emotion rating, or survey afterward.

**R1** was another practical finding. Participants were comfortable with roughly a minute, but longer exercises started losing their attention. That pushed me toward a planned 60-second session instead of a longer guided activity. I will still have to measure the real timing after I build it, since loading delays and transitions could make a difference.

I also wanted to make sure the user stays in control. **R3** focused on permission to stop, while **R4** had the most mentions among the requirements for controlling one's own journey. My design lets the user choose either skill, pause, or leave without a warning or penalty. The AI can make a suggestion, but it cannot select a skill for the user or make them finish one.

Safety was another major part of the feedback (**R2** and **D4**). I put a **Crisis info** control in the header of each screen in the mockup. It is supposed to open static support information, including 988 in the U.S., even when the model is unavailable. I do not want access to that information to depend on a chatbot response.

For the remaining principles, **D1** led me to a user-controlled *Simpler view* instead of trying to guess how distressed someone is. **D5** led to the idea of a *Repeat last skill* option, but only if a user has chosen