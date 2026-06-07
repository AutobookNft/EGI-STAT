# SOURCE MAP — dev-productivity-metrics

Reliability labels: **[PEER_REVIEWED]** academic/venue-reviewed · **[VENDOR_DOC]** vendor/tool docs (interest-conflicted) · **[PRACTITIONER]** expert essay/opinion · **[STANDARD]** official methodological standard.

## Frameworks (primary)

| # | Source | Authors / Org | Label | Used in |
|---|--------|---------------|-------|---------|
| 1 | *The SPACE of Developer Productivity* (ACM Queue, 2021) — https://queue.acm.org/detail.cfm?id=3454124 · summary https://getdx.com/research/space-of-developer-productivity/ | Forsgren, Storey, Maddila, Zimmermann, Houck, Butler (Microsoft Research / GitHub / Univ. Victoria) | [PEER_REVIEWED] | ch01, Core |
| 2 | DORA — *Accelerate* / DevOps Research & Assessment (Google); 4 keys + tiers — https://getdx.com/blog/dora-metrics/ · dora.dev | Forsgren, Humble, Kim et al. / Google | [PEER_REVIEWED] (Accelerate) + [VENDOR_DOC] (the linked guide) | ch02, Core |
| 3 | *DevEx: What Actually Drives Productivity* (ACM Queue, 2023) — https://queue.acm.org/detail.cfm?id=3595878 · summary https://develocity.io/a-summary-devex-what-actually-drives-productivity-by-noda-et-al-2023/ | Noda, Storey, Forsgren, Greiler | [PEER_REVIEWED] | ch03, Core |
| 4 | DX Core 4 (unification of DORA+SPACE+DevEx) — https://getdx.com/blog/dora-metrics/ | GetDX (Abi Noda) | [VENDOR_DOC] | ch02, Core |

## Anti-patterns / critique

| # | Source | Label | Used in |
|---|--------|-------|---------|
| 5 | Goodhart's Law applied to engineering metrics — codepulsehq.com/guides/goodharts-law-engineering-metrics · lawsofsoftwareengineering.com/laws/goodharts-law/ | [PRACTITIONER] | ch04, Core |
| 6 | *Why Lines of Code Are A Bad Measure* — workweave.dev/blog/why-lines-of-code-are-a-bad-measure-of-developer-productivity | [PRACTITIONER] | ch04 |
| 7 | *Measuring developer productivity? A response to McKinsey* (Pragmatic Engineer, 2 parts) — newsletter.pragmaticengineer.com/p/measuring-developer-productivity ; Kent Beck on LinkedIn | Orosz & Beck | [PRACTITIONER] | ch04, Core |
| 8 | *Yes, you can measure developer productivity* (McKinsey, Aug 2023) — the position being critiqued | McKinsey | [PRACTITIONER] (interest-conflicted) | ch04 |

## Statistics / index construction

| # | Source | Label | Used in |
|---|--------|-------|---------|
| 9 | *Handbook on Constructing Composite Indicators: Methodology and User Guide* (OECD/JRC, 2008) — https://www.oecd.org/content/dam/oecd/en/publications/reports/2008/08/...9789264043466-en.pdf | [STANDARD] | ch05, Core |
| 10 | *On the Methodological Framework of Composite Indices: weighting, aggregation, robustness* (Social Indicators Research, Springer) — link.springer.com/article/10.1007/s11205-017-1832-9 | [PEER_REVIEWED] | ch05 |
| 11 | Winsorization & robust statistics for skewed/log-normal data (DataCamp; Tulane; arXiv 2204.02477 on log-normal winsorized moments) | [PRACTITIONER] + [PEER_REVIEWED] | ch05 |
| 12 | Human Development Index — switch from arithmetic to geometric mean (2010) as the canonical non-compensatory-aggregation precedent (UNDP) | [STANDARD] | ch05 |

## Notes
- ACM Queue canonical PDFs returned HTTP 403 to automated fetch on 2026-06-07; SPACE/DevEx content corroborated via authors' summaries (getdx, develocity, Microsoft Research listing) and InfoQ coverage. Claims sourced this way carry `[SSOT_TRUST]` in the chapters.
- Vendor docs (getdx, linearb, harness) sell productivity tooling → treat tier thresholds and "DX Core 4" framing as interest-conflicted; the underlying DORA/SPACE/DevEx constructs are the peer-reviewed part.
