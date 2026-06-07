# ch04 — Anti-patterns: Goodhart, LOC/commits, McKinsey

> Sources: practitioner essays + the 2023 McKinsey debate [PRACTITIONER]. Claims are reasoned consensus, not RCT evidence — `[SSOT_TRUST]`.

## Goodhart's Law
> "When a measure becomes a target, it ceases to be a good measure."

Every productivity metric is a **proxy for value, not value**. Once people are rewarded on the proxy, they rationally optimize the proxy instead of the value. This is universal — sprint velocity, deploy frequency, LOC, commit count all succumb. **Defense**: keep metrics descriptive (system health) not targets (individual quotas); always carry a **counter-metric** so gaming one surfaces in another.

## Why LOC and commit counts are bad proxies
- A **40-line** solution can beat **400 lines** of boilerplate — LOC rewards the worse one.
- Deleting **2,000 lines** of dead code is *negative* productivity under LOC, though it's often the most valuable work.
- Commit count rewards **many small commits** over one correct commit; trivially padded.
- LOC/commits are **byproducts**, not results. "A line of code that doesn't solve a problem is worse than no code."
- Gaming is **trivial**: a per-LOC reward could be maxed in a day with zero business value.

**Consequence for EGI-STAT**: any index dominated by `weighted_commits` (= count × tag weight) and raw `lines` inherits all of this. It must (a) be quality-paired, (b) never rank individuals, (c) be honest that it measures *output volume*, not *value delivered*.

## The McKinsey 2023 controversy
McKinsey published *"Yes, you can measure developer productivity"* proposing individual "contribution analysis." Kent Beck (creator of XP) and Gergely Orosz (Pragmatic Engineer) rebutted at length:
- It measures **effort/output, not outcomes/impact** — missing half the software lifecycle.
- **Individual-level** tracking reads as **surveillance**, makes engineers feel unsafe, and damages culture for years.
- Output is necessary but not sufficient; what matters is whether the output produced an outcome.

**Takeaways encoded as rules**:
1. Measure at **team/system** level, never to rank individuals.
2. Distinguish **output** (we did X) from **outcome/impact** (X helped) — and never sell output as productivity.
3. Frame metrics as **"improve the system,"** not "evaluate the person."
4. Be transparent about what the metric *cannot* see.

## How this constrains an EGI-STAT redesign
The redesign may legitimately produce a **team/system-level Output (Activity) index** for the whole ecosystem, paired with a quality counter-metric, explicitly labeled as output-not-impact. It may **not** be used as a per-developer score, and the dashboard copy should say what it omits (Satisfaction, real Performance/impact, DevEx perceptions).
