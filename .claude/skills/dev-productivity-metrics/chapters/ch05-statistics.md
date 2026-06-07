# ch05 — The statistics of an honest composite index

> Sources: OECD/JRC *Handbook on Constructing Composite Indicators* (2008) [STANDARD]; Greco et al. on weighting/aggregation/robustness (Soc. Indicators Research) [PEER_REVIEWED]; robust-statistics literature [PRACTITIONER/PEER_REVIEWED].

A "Productivity Index" that fuses commits, lines, files, etc. **is** a composite indicator. The OECD handbook gives the disciplined 10-step recipe. The steps that matter here:

## 1. Theoretical framework first
Decide *what the index means* before any math. "Output volume of the ecosystem per week" is a defensible target; "productivity" (unqualified) is not (ch01/ch04). Each sub-indicator must be justified by that frame (P0-3: explicit, no hidden assumptions).

## 2. Handle the data distribution — software metrics are right-skewed
Commits/lines/files per mission are **log-normal-ish**: most small, a few enormous (M-OS3-093: 13 commits; M-OS3-088: 7 200 lines in 1 commit). Two consequences:
- **Raw sums are outlier-dominated** — one giant mission swamps the week.
- **Hard caps are arbitrary** — EGI-STAT's `min(|net|, 2000)` is an undocumented magic constant that silently equates a 2 001-line and a 20 000-line mission.

**Principled alternatives**:
- **Log transform**: `log1p(x)` compresses the tail, keeps monotonicity, no magic constant. Diminishing returns are *built in* (the 10 001st line counts less than the 11th) — which is usually what you actually want.
- **Winsorization**: replace values above the p95 (or p99) with the p95 value — caps influence at a *data-driven* threshold, not a guessed one.
- **Robust center/scale**: median and **MAD** (median absolute deviation); `robust_z = (x − median) / (1.4826·MAD)` ≈ a z-score that ignores outliers (1.4826 makes MAD≈σ for normal data).

## 3. Normalize before combining unlike units
You cannot add `weighted_commits·10 + lines/10` — the ×10 and /10 are invented weights and the units differ. Normalize each sub-indicator to a common scale first:
- **z-score** (OECD default; mean 0, sd 1) — good when distributions are ~symmetric *after* log.
- **robust z** (median/MAD) — better for residual skew.
- **min-max → [0,1]** — interpretable, but sensitive to the extremes (winsorize first).
Then weights become **explicit and inspectable**.

## 4. Weighting
Weights encode value judgments — make them explicit (CEO decision, P0-3). **Equal weighting** is the honest default unless you have a reason. Options: equal, expert/budget-allocation, or data-driven (PCA) — but PCA weights are hard to explain to a CEO; prefer equal or expert weights for a dashboard.

## 5. Aggregation — compensatory vs not
- **Arithmetic mean** = *compensatory*: a high commit count compensates a near-zero quality. Gameable.
- **Geometric mean** = *partially non-compensatory*: any dimension near zero drags the whole index down — you can't fully offset weakness on one axis with strength on another. The **Human Development Index switched arithmetic→geometric in 2010** for exactly this reason.
Use **geometric mean across dimensions** (output × quality) so throughput can't fully mask breakage.

## 6. Throughput vs average — the central distinction
- **Sum / throughput** answers *"how much did we produce?"* — scales with volume (159 missions > 11 missions). Outlier-sensitive → aggregate **normalized/log** sub-scores, not raw.
- **Average / rate** answers *"how good/intense was each unit?"* — volume-invariant.
These are **different metrics**. EGI-STAT's bug is showing an **average** (`AVG(productivity_index)`) where the user expects **throughput**. A dashboard should carry **both, labeled** (e.g. "Output settimanale" = throughput; "Intensità media per missione" = average).

## 7. Robustness / sensitivity analysis
Before trusting the index, perturb the choices (weights ±, cap p95↔p99, arithmetic↔geometric) and check whether the **week-to-week ranking is stable**. If small changes reorder the weeks, the index is an artifact of arbitrary constants, not a signal. Report the check.

## Minimal honest recipe (what ch06 instantiates)
```
per mission i:
  v_i = geomean( norm(log1p(value_axis_i)), norm(quality_axis_i) )   # 0..1-ish, non-compensatory
weekly_throughput = Σ_i v_i        # "how much" — scales with volume
weekly_intensity  = mean_i v_i     # "how good each" — volume-invariant
# both shown; weights explicit; caps via winsorize; no magic ×10//10/2000.
```
