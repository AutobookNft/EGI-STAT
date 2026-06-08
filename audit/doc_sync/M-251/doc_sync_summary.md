# DOC-SYNC v2 — M-251 (EGI-STAT)

> Esito: success (con 1 patch SSOT cross-organo PROPOSTA, da applicare a mano)
> Modalita: LSO ridotta (nessun SSOT_REGISTRY.json, nessun RAG_SCHEMA) + cross-organ.
> Trigger Matrix: tipo 2 (comportamentale).

## Cosa ha cambiato M-251
1. `backend/aggregate_to_sqlite.aggregate()` — il rebuild atomico ora parte da una COPIA
   (`shutil.copy2`) del DB esistente, cosi' le tabelle NON gestite da aggregate
   (`legacy_production`/`legacy_repo_day`) sopravvivono al rebuild. Fix regressione M-250.
   Nuova invariante: ogni tabella non-gestita persiste attraverso ogni rebuild del serving.
2. `frontend/.../AddTimeModal.jsx` — riga TOTALE (`<tfoot>`) nella tabella Ore per Progetto.
3. `backend/tests/m_251_preserve_legacy_test.py` — test che cattura la regressione (RED→GREEN).

## SSOT impattati
- **os3-matrix/docs/stats/STATS_SYSTEM_SSOT.md** (cross-organo, FUORI instance_root): impattato.
  Il SSOT documenta gia' il rebuild atomico e il "degrado pulito" quando `legacy_production` e'
  assente, MA non l'invariante di PRESERVAZIONE delle tabelle legacy attraverso il rebuild.
  Lacuna ADDITIVE. Patch proposta in `diffs/STATS_SYSTEM_SSOT.proposed.md`.
  NON auto-applicata: cross-project (cross-project-guard) + fuori scope mission. Da applicare a mano.
- In-instance: nessun SSOT (EGI-STAT non ha registry/doc SSOT — coerente con M-220/M-221).
- Frontend riga TOTALE: no_change (presentazionale, nessun SSOT a quella granularita').

## Step eseguiti / skippati
- Step 1 (analisi semantica): OK → mission_semantic_summary.json
- Step 2 (SSOT diretti): degradato (no registry) → directly_impacted_ssots.json (asserzione manuale)
- Step 3 (RAG discovery): SKIP (no RAG_SCHEMA)
- Step 4 (discriminazione + patch): OK → doc_sync_actions.json + diff proposto
- Step 5 (RAG reindex): SKIP (no RAG_SCHEMA)
- Step 5b (metadati registry): SKIP (no SSOT_REGISTRY.json)
- Step 6 (audit + log): OK

## Azione richiesta all'operatore
Applicare a mano il blockquote M-251 in STATS_SYSTEM_SSOT.md (vedi diff). Posizione suggerita:
dopo il blockquote "Auto-refresh read-time (M-247)" (~riga 338). E' un'aggiunta; nessun residuo
versione/concetto da riconciliare.

## Note coerenza con CLAUDE.md EGI-STAT
Il CLAUDE.md istanza dichiara "Strumento interno — nessun DOC-SYNC richiesto su EGI-DOC". Questo non
e' un sync verso EGI-DOC: e' la proposta di una nota sul SSOT del SISTEMA STATISTICHE (os3-matrix),
che M-251 ha cambiato comportamentalmente. La proposta e' coerente col Pilastro 5 (doc co-evolve col
codice); l'applicazione resta decisione/azione manuale dell'operatore.
