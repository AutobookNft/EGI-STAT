# DOC-SYNC v2 — M-252 (EGI-STAT)

> Esito: **success** · rag_mode: **skipped_no_schema** (LSO ridotto) · Trigger=2

## Contesto
M-252 (organo EGI-STAT) rende `aggregate_daily` **mission-only** (coerenza card↔grafico, decisione CEO
"stat solo dentro mission"), introduce il pattern mission-ID canonico `ecosystem.MISSION_ID_RE` +
`cites_mission()` con test anti-drift, e aggiunge un guard anti-mis-attribuzione in `coherence_check.py`.

## Particolarità di questa esecuzione
- **EGI-STAT non ha un `docs/lso/SSOT_REGISTRY.json` proprio.** Per stretto protocollo questo darebbe
  `ssot_registry_not_found`. Tuttavia il prompt di mission indica **esplicitamente** il SSOT impattato —
  `os3-matrix/docs/stats/STATS_SYSTEM_SSOT.md` (nel repo engine, che HA un suo registry) — con direttiva
  chiara ("segnala/applica la nota se opportuno"). Direttiva esplicita ≠ deduzione: ho proceduto in
  **modalità LSO ridotto** (no RAG → Step 3 e Step 5 skippati) trattando quel SSOT come impatto diretto.
- **Gap di watch (informativo).** Nel registry os3-matrix l'entry STATS_SYSTEM_SSOT ha `watches.paths=[]`
  e `watches.repos=["os3-matrix"]`: non aggancia i file `EGI-STAT/backend/*`. Il matching deterministico
  standard non avrebbe trovato questo SSOT. Suggerimento non bloccante: aggiungere ai watches i path
  `EGI-STAT/backend/{stats_v2.py,ecosystem.py,tools/coherence_check.py}` o il repo `EGI-STAT`.

## SSOT modificato (1, sostitutivo)
`os3-matrix/docs/stats/STATS_SYSTEM_SSOT.md` — **substitutive**, status **applied**.

Il SSOT descriveva (M-OS3-082/M-OS3-083) `aggregate_daily = mission_repo_day UNION ALL legacy_repo_day`
con time-series sull'intera storia: **contraddiceva il codice M-252**. Patch:
1. front-matter `last_updated_mission` → M-252;
2. blocco "Effetto sulla time-series" (M-OS3-082) riscritto: la UNION è marcata **SUPERATA da M-252**,
   sorgente corrente = solo `mission_repo_day` (storia preservata, non cancellata — Step 4.3.4);
3. blocco "Distinzione da non confondere" riscritto: card e grafico ora **coincidono** (mission-only);
4. coda paragrafo M-OS3-083: nota ⚠️ M-252 (filtri operano su time-series mission-only);
5. **3 nuove sezioni**: *Time-series mission-only — card==grafico*, *Pattern mission-ID canonico
   (MISSION_ID_RE/cites_mission + test anti-drift)*, *Guard anti-mis-attribuzione in coherence_check*.

Verifica esaustività (`grep "UNION ALL legacy_repo_day"`): nessuna asserzione **corrente** residua del
vecchio comportamento; tutti i residui sono riferimenti **storici** legittimi (righe 227/233/256/665).

Hash prima: `1d019806…` → dopo: `f3e11fc5…`. Diff: `diffs/STATS_SYSTEM_SSOT.md.diff`.

## Metadati registry
`os3-matrix/docs/lso/SSOT_REGISTRY.json` entry [11]: `last_verified=2026-06-09`,
`verified_in_mission=M-252`, `verification_mode=registry_only`, `last_drift_score=0`.

## Coverage check
Nuovi file mission = solo test (`m_252_canonical_id_test.py`, `m_252_card_weekly_coherent_test.py`).
Nessun file di produzione nuovo non coperto da SSOT.

## Governance / azione richiesta all'operatore
La patch è **applicata su disco** in os3-matrix ma **non committata**: il SSOT vive nel repo engine
(governance os3-matrix, finora verificato da M-OS3-105). Cross-repo + sostitutivo = Trigger Matrix tipo 6.
La sostanza è decisione CEO già registrata (commit b9328f7 + prompt). **Resta all'operatore committare
il file os3-matrix** e valutare l'aggiornamento dei `watches` (gap segnalato sopra).
