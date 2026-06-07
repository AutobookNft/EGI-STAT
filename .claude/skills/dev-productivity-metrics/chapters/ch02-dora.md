# ch02 — DORA + DX Core 4

> Source: Google DevOps Research & Assessment / *Accelerate* [PEER_REVIEWED]; tier guide [VENDOR_DOC].

## The four keys (two clusters)

### Throughput
1. **Deployment Frequency** — how often code reaches production. Count deploys from CI/CD or git tags.
2. **Lead Time for Changes** — time from commit to running in production. Timestamp commit → deploy.

### Stability
3. **Change Failure Rate** — % of deploys causing a production failure needing remediation.
4. **Time to Restore / MTTR** — average time to recover service after a failed change.

## Performance tiers (indicative)
| Metric | Elite | High | Medium | Low |
|---|---|---|---|---|
| Deploy freq | multiple/day | daily–weekly | weekly–monthly | monthly–6mo |
| Lead time | <1 day | 1d–1wk | 1wk–1mo | 1–6mo |
| Change-fail rate | 0–15% | 16–30% | … | 46–60% |
| MTTR | <1h | <1d | 1d–1wk | 1wk–1mo |

## The lesson that transfers to ANY index
**Pair throughput with stability.** High performers are good at *all four simultaneously* — they don't trade stability for speed. If your metric rewards only throughput (more commits, more missions), it is gameable by shipping fast and breaking things. Always carry a **counter-metric** from the quality/stability side.

## DX Core 4 (the unification)
GetDX's framework folding DORA + SPACE + DevEx into four axes: **Speed · Effectiveness · Quality · Business impact**. Treat as a practical checklist of what a complete program covers — not as peer-reviewed canon (vendor framing). [VENDOR_DOC]

## EGI-STAT reality check
EGI-STAT has **no deploy/incident telemetry** (it is read-only over git + the mission registry). Therefore DORA's two stability keys (change-fail rate, MTTR) and deployment frequency are **not measurable** from current data. The closest available proxies:
- *Lead time* ≈ mission `date_opened → date_closed` (already in the DB).
- *Stability/quality* ≈ ratio of `[FIX]`/`[REVERT]` follow-ups to `[FEAT]` (a rework signal), or `closed_with_debt` rate. These are weak proxies — document them as such.
