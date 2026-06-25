# DOC-SYNC v2 — M-STAT-002

> Mission: producer `drift.json` ship-with-push per il cockpit Nexus (gemello del serving M-NEXUS-009).
> Instance: /home/fabio/EGI-STAT — LSO ridotto (no `docs/lso/SSOT_REGISTRY.json`, no RAG_SCHEMA).
> Esito: success — 1 SSOT documentale aggiornato (additivo).

## Cambiamento analizzato
- `backend/produce_drift.py` (NUOVO): esegue `ssot-index-check` sul laptop, serializza l'esito in `data/drift.json` (campi `has_drift`/`returncode`/`raw`/`generated_at`; conservativo: check irraggiungibile → `has_drift True`).
- `backend/tests/m_stat_002_drift_producer_test.py` (NUOVO): test P0-13, 3/3.
- `deploy/push-stats-nexus.sh` (MODIFICATO): step 1c genera `drift.json`, step 2c `s3 cp`, pull SSM lo tira giù sul box.

## SSOT impattati
EGI-STAT non ha SSOT registry formale. Per scoperta documentale, l'unico doc che descrive la pipeline stat/push e gli artefatti ship-with-push è **`backend/MULTI_REGISTRY.md`** — già toccato da DOC-SYNC in M-266, M-221, M-STAT-001.

| SSOT | Mode | Status |
|---|---|---|
| `backend/MULTI_REGISTRY.md` | additive | applied |

## Patch applicata (additiva)
Aggiunta una nuova sottosezione **"### Drift SSOT — secondo artefatto ship-with-push (M-STAT-002, ...)"** sotto la §M-FUC-057 (ship-with-push). Documenta `produce_drift.py`, il vincolo topologico (check valido solo sul laptop), gli step 1c/2c del push + pull SSM, la specularità col serving M-NEXUS-009, e dichiara esplicitamente che gli artefatti ship-with-push del push stat sono **ora 3** (`stats.db` + `coverage.json` + `drift.json`).

La §M-FUC-057 preesistente NON è stata modificata: è record storico legittimo (quando fu scritta si spediva solo `coverage.json`). Verifica esaustività: `grep` di `coverage.json`/`ship-with-push`/`push-stats`/`drift` nel doc → unico punto-lista degli artefatti aggiornato; nessun altro doc fuori da `audit/` cita gli artefatti spediti.

## Step saltati (LSO ridotto)
- Step 3 (discovery RAG): skip — nessun RAG_SCHEMA.
- Step 5 (RAG re-index / rag-distribute): skip — nessun store RAG per EGI-STAT.
- Step 5b (metadati SSOT_REGISTRY): skip — file registry assente.
