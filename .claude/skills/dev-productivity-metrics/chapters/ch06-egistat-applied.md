# ch06 — Applied to EGI-STAT: auditing & redesigning the Indice di Produttività

> Uses ch01–ch05 to (a) state what EGI-STAT's data can legitimately measure and (b) redesign the index. Evidence from `data/stats.db`, 318 closed missions, 2026-06-07.

## What EGI-STAT data CAN and CANNOT measure
EGI-STAT is read-only over **git commits + the mission registry**. Mapping to SPACE/DORA/DevEx:
| Dimension | Measurable here? | From what |
|---|---|---|
| SPACE Activity | ✅ | commits, lines, files, tags, missions closed |
| SPACE Efficiency (lead time) | ⚠️ partial | mission `date_opened → date_closed` |
| SPACE Performance (outcome) | ❌ mostly | no incident/adoption data; weak proxy = FIX/REVERT rework ratio |
| SPACE Satisfaction | ❌ | needs a survey |
| DORA throughput (deploy freq, lead time) | ⚠️ proxy | mission cadence, not real deploys |
| DORA stability (CFR, MTTR) | ❌ | no deploy/incident telemetry |
| DevEx (all three) | ❌ | perceptual; system half only, weakly |

**Honest conclusion**: every current EGI-STAT number lives in SPACE's **Activity** dimension. The index must therefore be **named and sold as an OUTPUT/Activity index**, at **team/system level**, never as "productivity" of a person (ch01, ch04). A *real* productivity read needs a recurring developer survey (ch03) — the single highest-value future addition.

## The four defects of v2 (diagnosed, with evidence)
The v2 formula ([ingest_missions.py:256](../../../backend/ingest_missions.py) `compute_productivity`) and the weekly serving ([stats_v2.py:184](../../../backend/stats_v2.py) `AVG(productivity_index)`):

1. **Throughput-blind (worst).** The chart plots `AVG(productivity_index)` per mission. W23 closed **159** missions (output ~4× any week) but displayed **25.0** — *lower* than W19's 55.5 (17 missions). An average answers "how good each unit," not "how much produced" (ch05 §6).
2. **Magic cap.** `capped = min(|net|, 2000); base += capped/10` → a 2 001-line and a 20 000-line mission are equal. The data is log-normal (lines_added mean/median = **3.9**, max **67 315** vs p50 **266**) → a *data-driven* winsorize or a `log1p` is the principled replacement (ch05 §2).
3. **Double volume penalty.** `pi = base · mult / cognitive_load`, and `cognitive_load` itself grows with log(lines·files·commits) → bigger work inflates the denominator. `cognitive_load` saturates at its 3.5 cap for the p90+ of missions, so it mostly just *divides large work down*. Complexity is already in the log terms; dividing again double-counts (ch05 §1, §6).
4. **Implicit weights.** `weighted·10 + capped/10` mixes unlike units (commit-count vs lines) with invented ×10//10 weights, and `weighted` is **commit-count-driven**, so many-small-commits beats one-correct-commit (ch04 LOC/commit anti-pattern). Violates P0-3 (no hidden parameters).

## The v3 redesign (grounded in ch05's recipe)
Reference implementation: [`backend/productivity_v3.py`](../../../backend/productivity_v3.py). Per mission:
```
output(m) = 0.60·log1p(lines_touched) + 0.25·log1p(files) + 0.15·log1p(commits)   # explicit weights, no cap
value(m)  = effort_mult(dominant_tag) · output(m)                                  # intent/quality, explicit table
```
Then **two distinct, labeled** weekly metrics (ch05 §6) — never one:
- **Throughput** = `Σ value(m)` → "quanto abbiamo prodotto" (scales with volume).
- **Intensità** = `mean value(m)` → "quanto era denso/qualificato ogni lavoro" (volume-invariant).

What it fixes vs the checklist (SKILL Core):
- ✅ sum vs average made explicit (defect 1)
- ✅ `log1p` instead of magic cap (defect 2)
- ✅ no `÷cognitive_load` (defect 3)
- ✅ explicit documented weights, no ×10//10 (defect 4)
- ✅ stays team/system level, named "Output", not per-developer "productivity" (ch04)

### Evidence the redesign behaves
Recent weeks (v2 vs v3):
| week | #miss | v2 AVG (chart) | v2 SUM | **v3 throughput** | v3 intensità |
|---|---:|---:|---:|---:|---:|
| 2026-W19 | 17 | 55.5 | 944 | 81.8 | 4.81 |
| 2026-W21 | 11 | 17.0 | 187 | 19.6 | 1.78 |
| **2026-W23** | **159** | **25.0** | 3969 | **577.4** | 3.63 |

v3 throughput correctly makes W23 dominate (577 vs next-highest 117); intensità stays mid (3.63) — telling the true story: *a huge volume of mostly normal-density missions*. The two numbers together are the SPACE-style multi-signal read.

## Still NOT covered (state it on the dashboard — ch04 rule 4)
Quality/outcome (real Performance), Satisfaction, DevEx perceptions. v3 is an **Output index**, not "productivity". Pairing it with a quality counter-metric (e.g. rework ratio = FIX-lines following a FEAT mission) would move it toward a DORA-style throughput+stability pair — a sensible next mission, **pending CEO approval** since it redefines metric semantics (Trigger Matrix 3).
