# ch03 — DevEx (Noda, Storey, Forsgren, Greiler, 2023)

> Source: *DevEx: What Actually Drives Productivity*, ACM Queue 2023 [PEER_REVIEWED]. Distils 25 sociotechnical factors into 3 dimensions.

## Why it exists
DORA measures delivery; SPACE frames the space. DevEx explains **what actually makes a developer productive day to day** — the friction of turning an idea into shipped software. Productivity is downstream of experience.

## The three dimensions

1. **Feedback Loops** — speed & quality of response to a developer's action. Fast loops (quick builds, quick tests, quick reviews) keep work moving; slow loops cause context-switching and frustration.
   System measures: build time, test-suite time, PR review turnaround, CI wait. Perceptual: "how satisfied are you with feedback speed?"

2. **Cognitive Load** — mental effort a task demands. Complex code + complex process = high load = slower work, more errors.
   System measures: code complexity, # systems to touch for a change, doc findability. Perceptual: "how hard is it to understand/deploy this code?"
   ⚠️ EGI-STAT's `cognitive_load` column is a *derived complexity proxy* (log of lines/files/commits), **not** the DevEx construct (which is largely perceptual). Don't conflate them.

3. **Flow State** — sustained, energized focus. Killed by interruptions, unplanned work, fragmented calendars, slow loops, high load.
   System measures: meeting load, fragmentation of focus blocks, unplanned-work ratio. Perceptual: "how often do you reach flow?"

## Measurement rule
Always combine **perceptions (surveys) + system/workflow data**. Each catches what the other misses: a fast review can still *feel* disruptive; a build can be slower than anyone notices. EGI-STAT has only system data → it can, at best, approximate the system half of Feedback Loops and Cognitive Load; the perceptual half is unmeasurable without a developer survey.

## Implication
If FlorenceEGI ever wants a *real* productivity read (not just an output count), the cheapest high-value addition is a short, recurring developer survey (a handful of DevEx/SPACE perceptual items). Without it, every EGI-STAT number lives inside SPACE's **Activity** dimension only.
