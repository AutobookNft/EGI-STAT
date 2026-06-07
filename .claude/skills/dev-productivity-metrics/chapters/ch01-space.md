# ch01 — SPACE (Forsgren, Storey et al., 2021)

> Source: *The SPACE of Developer Productivity*, ACM Queue 2021 [PEER_REVIEWED]. Concrete metric tables corroborated via authors' summaries [SSOT_TRUST].

## Thesis
Developer productivity is **not** an individual's activity level and **not** the efficiency of one system. It is multi-dimensional and **cannot be measured by a single metric or dimension**. SPACE exists to stop teams from reducing productivity to "commits" or "velocity."

## The five dimensions

### S — Satisfaction & well-being
How fulfilled, healthy, and happy developers are with work, team, tools, culture.
Examples: developer satisfaction survey / eNPS, perceived productivity, burnout indicators, retention/attrition.
*Mostly perceptual — requires surveys.*

### P — Performance
The **outcome** of the work (not the act of producing it). Hard because the link between an individual's output and an outcome is loose.
Examples: change-fail rate, incident count/severity, reliability/uptime, % of work that meets its goal, customer adoption/satisfaction of shipped work.

### A — Activity
A **count of outputs/actions** during work. Easy to collect, easy to **misuse** — activity is the dimension Goodhart hits hardest.
Examples: commits, pull requests, **lines of code**, builds, deploys, code-review comments, documents written.
*Useful only alongside other dimensions; never alone, never per-individual as a target.*

### C — Communication & collaboration
How work and knowledge flow between people.
Examples: PR review latency, time-to-onboard, discoverability of docs, who-reviews-whom network, quality of integration across teams.

### E — Efficiency & flow
Ability to make progress with minimal interruption/delay.
Examples: lead time, number of handoffs, wait/queue time, % of uninterrupted focus time, perceived ability to get into flow.

## The usage rules (the part people skip)
1. **Never one metric.** A single number is meaningless and gameable.
2. **Span ≥3 dimensions.** A balanced read needs breadth, not depth on Activity.
3. **Include ≥1 perceptual metric.** System data alone misses satisfaction/flow; surveys catch what logs can't.
4. **Capture tradeoffs.** Pair metrics so gaming one shows up in another (e.g. throughput ↑ but change-fail-rate ↑ = not a win).
5. **Right level.** Report at team/system level. Individual-level activity metrics are explicitly flagged as dangerous (surveillance, gaming, demoralization).

## Implication for a "Productivity Index"
A composite Activity-only index (commits + LOC + files, however weighted) sits **entirely inside the Activity dimension**. By SPACE's own standard it is at best *one signal*, mislabeled if presented as "productivity." The honest fix is either (a) rename it to what it is (an Activity/Output index) or (b) add Performance and Efficiency signals (e.g. mission lead time, rework rate) and report them side by side.
