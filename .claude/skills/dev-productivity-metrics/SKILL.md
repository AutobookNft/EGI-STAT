---
name: dev-productivity-metrics
description: "Knowledge base on MEASURING SOFTWARE-DEVELOPER PRODUCTIVITY — the real, sourced state of the art, for designing or auditing a productivity metric/index. Covers the three canonical frameworks: SPACE (Forsgren, Storey et al., 2021, ACM Queue — 5 dimensions Satisfaction/Performance/Activity/Communication/Efficiency, the 'never one metric' rule), DORA (Google DevOps Research — 4 keys: deployment frequency, lead time, change-failure-rate, MTTR, split into throughput vs stability), and DevEx (Noda/Storey/Forsgren/Greiler, 2023, ACM Queue — feedback loops, cognitive load, flow state); plus DX Core 4 (the unification). Covers the ANTI-PATTERNS: Goodhart's Law (measure→target→gamed), why LOC/commit counts are bad proxies, the 2023 McKinsey controversy (Beck/Orosz: output≠outcome, individual surveillance harm). Covers the STATISTICS of building a defensible composite index: OECD 10-step handbook, normalization (z-score/min-max/robust), log-transform & winsorization for skewed software metrics, median+MAD robust scaling, arithmetic (compensatory) vs geometric (non-compensatory) aggregation, throughput-vs-average distinction. Use when designing, redesigning, auditing, or critiquing any developer-productivity metric, score, index, or dashboard (e.g. EGI-STAT's Indice di Produttività) — to ground the choice in real research instead of inventing, and to know what a given data set CAN and CANNOT legitimately measure. SISTER SKILLS — for choosing product success metrics (North Star/AARRR) use product-metrics; for CI/CD delivery measurement mechanics use ci-cd-delivery; for the statistics of evaluation suites use evaluation."
allowed-tools:
  - Read
  - Grep
argument-hint: [topic or chapter — e.g. space, dora, devex, goodhart, statistics, egistat]
---

# Measuring Developer Productivity
**Frameworks**: SPACE · DORA · DevEx · DX Core 4 | **Sources**: peer-reviewed + practitioner (see SOURCE_MAP.md) | **Generated**: 2026-06-07

> Built for FlorenceEGI / EGI-STAT to put the *Indice di Produttività* on a defensible footing. Reliability labels per source in `SOURCE_MAP.md`. This skill teaches **how productivity is measured in the literature** and **the statistics of building an honest index** — not how to ship a dashboard.

## How to Use This Skill

- **No argument** — load the Core below (the canon + the anti-patterns + the statistics in brief).
- **With a topic** — `space`, `dora`, `devex`, `goodhart` / `antipatterns`, `statistics` / `composite-index`, `egistat`; I read the matching chapter.
- **Browse** — ask "what chapters?" for the index.

When asked something not in Core, read the relevant `chapters/*.md` before answering. Numbers/claims in chapters carry uncertainty labels where the source is opinion not evidence.

---

## Core — the one thing to remember

> **Productivity cannot be captured by a single metric, and any single proxy you optimize gets gamed.** Every credible framework since 2021 (SPACE, DevEx, DX Core 4) is *multi-dimensional by design*. A single "Productivity Index" number is, by the literature's own standard, an anti-pattern — defensible only as one **Activity** signal among several, never as "the" productivity. `[SSOT_TRUST]` (SPACE; Goodhart)

### The three canonical frameworks

**SPACE** (Forsgren, Storey, Maddila, Zimmermann, Houck, Butler — 2021, ACM Queue). Five dimensions; you are told to pick metrics from **several** of them, never one:
| Dim | Meaning | Example metrics |
|---|---|---|
| **S**atisfaction & well-being | how fulfilled/healthy devs feel | survey eNPS, burnout, retention |
| **P**erformance | outcome/quality of what's produced | change-fail rate, reliability, MTTR, % work meeting goals |
| **A**ctivity | count of outputs | commits, PRs, **LOC**, builds, code-review count |
| **C**ommunication & collaboration | how work flows between people | PR review latency, onboarding time, network of contributors |
| **E**fficiency & flow | uninterrupted forward progress | lead time, handoffs, wait time, % time in flow |

SPACE's explicit rules: (1) **never a single metric**; (2) use metrics from **≥3 dimensions**; (3) include **≥1 perceptual (survey)** metric, not only system data; (4) **capture tradeoffs** (one metric up shouldn't silently push another down); (5) report at the right **level** (individual / team / system) — individual-level activity metrics are the most dangerous.

**DORA** (Google DevOps Research & Assessment). Four keys, two clusters — you need **both** clusters or you reward speed that breaks prod:
- *Throughput*: **Deployment Frequency**, **Lead Time for Changes**.
- *Stability*: **Change Failure Rate**, **Time to Restore (MTTR)**.
Tiered elite→low. Lesson for any index: **pair a throughput axis with a quality/stability axis** so they can't be gamed independently.

**DevEx** (Noda, Storey, Forsgren, Greiler — 2023, ACM Queue). Three dimensions of the *experience* that drives productivity: **Feedback Loops** (speed of response to an action), **Cognitive Load** (mental effort a task demands), **Flow State** (sustained focus). Measured with **perceptions (surveys) + system data** together. Note: EGI-STAT's existing "cognitive_load" borrows this name but is a derived complexity proxy, not the DevEx construct.

**DX Core 4** unifies the above into four dimensions — **Speed, Effectiveness, Quality, Business impact** — i.e. DORA's delivery + SPACE/DevEx's people/quality.

### The anti-patterns (what NOT to do)

- **Goodhart's Law**: "when a measure becomes a target it ceases to be a good measure." LOC/commits are *trivially* gamed (boilerplate, comment-padding, avoiding refactors). `[SSOT_TRUST]`
- **LOC is not output**: a 40-line solution beats 400 lines of boilerplate; deleting 2,000 dead lines is *negative* under LOC. Count of commits rewards many-small-commits over one-correct-commit. `[SSOT_TRUST]`
- **McKinsey 2023 controversy**: Beck & Orosz — measuring **effort/output ≠ outcomes/impact**; individual-developer "contribution analysis" reads as surveillance and harms culture. Keep metrics at **team/system** level, frame as *improving the system*, not ranking people. `[SSOT_TRUST]`

### The statistics of an honest index (OECD composite-indicator method)

When you must combine sub-metrics into one number, the OECD 10-step handbook is the reference. Key decisions:
1. **Software metrics are right-skewed / log-normal** (a few huge commits/missions dominate). Raw sums are outlier-driven. → **log-transform** heavy-tailed inputs, or **winsorize** at a percentile (e.g. cap at p95) instead of an **arbitrary hard constant** (EGI-STAT's `min(net,2000)` is an undocumented magic cap — winsorization is the principled version).
2. **Normalize before combining** unlike-unit metrics: **z-score** (OECD's recommended default), or **robust z** = (x − median)/(1.4826·MAD) for skewed data, or min-max to [0,1]. Never add raw `weighted*10 + lines/10` — the weights are implicit and unit-arbitrary.
3. **Aggregation**: **arithmetic mean = compensatory** (high commits hide low quality); **geometric mean = partially non-compensatory** (a near-zero dimension drags the whole score — good when you don't want one axis to mask another, cf. the HDI switched to geometric mean in 2010).
4. **Throughput vs average — the central EGI-STAT bug**: an *average per unit* (avg PI per mission) is **throughput-blind** — a week closing 159 missions scores like a week closing 3. Decide explicitly whether the metric answers "how much did we produce" (→ a **sum/throughput**) or "how good was each unit" (→ an **average/rate**). They are different metrics; a dashboard usually needs **both**, labeled.
5. **Robustness**: run an uncertainty/sensitivity check — does the ranking of weeks survive reasonable changes in weights/caps? If not, the index is an artifact of arbitrary constants.

### Decision checklist for any productivity metric

```
1. Is it ONE number sold as "productivity"?        → reframe as multi-signal (SPACE)
2. Throughput question or quality question?          → pick sum vs average EXPLICITLY (P0-3)
3. Throughput axis paired with a quality axis?       → else it gets gamed (DORA)
4. Inputs skewed/heavy-tailed?                        → log/winsorize, not hard caps
5. Unlike units summed raw?                           → normalize (z / robust-z / min-max)
6. One axis silently masking another?                → geometric mean, not arithmetic
7. Magic constants (×10, /10, cap 2000, /cl)?         → document each or remove (P0-3)
8. Used to rank individuals?                          → stop; team/system level only
9. Can a dev trivially game it?                       → Goodhart; add a counter-metric
```

---

## Chapters (read on demand)

- `chapters/ch01-space.md` — SPACE in full: 5 dimensions, metric examples, the usage rules.
- `chapters/ch02-dora.md` — DORA 4 keys, tiers, throughput vs stability, DX Core 4.
- `chapters/ch03-devex.md` — DevEx: feedback loops / cognitive load / flow; perceptions+system.
- `chapters/ch04-antipatterns.md` — Goodhart, LOC/commits, McKinsey controversy, surveillance harm.
- `chapters/ch05-statistics.md` — OECD composite indicators, normalization, skew/winsorize/log, robust z, arithmetic vs geometric, sum vs average, sensitivity analysis.
- `chapters/ch06-egistat-applied.md` — mapping the canon to EGI-STAT's available data (git + mission registry): what it CAN and CANNOT measure, and the redesign of the Indice di Produttività.

See `SOURCE_MAP.md` for every source and its reliability label.
