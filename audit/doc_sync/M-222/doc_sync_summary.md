# DOC-SYNC M-222 — EGI-STAT: tutti i repo del CEO nei grafici giornalieri

> doc_sync_version 2.2.0 — instance_root /home/fabio/EGI-STAT
> outcome: success — rag_mode: skipped_no_schema (LSO ridotto: nessun SSOT_REGISTRY.json)
> date: 2026-06-01

## Modalità
EGI-STAT non ha `docs/lso/SSOT_REGISTRY.json` né `RAG_SCHEMA`. DOC-SYNC opera in modalità
**LSO ridotto**: nessuna discovery deterministica via registry, nessun RAG (Step 3/5 skip).
Gli SSOT documentali sono i markdown diretti (`backend/MULTI_REGISTRY.md`, `README.md`).

## Step 1 — Analisi semantica
Mission additiva-comportamentale (Trigger Matrix tipo 2): aggiunge 3 repo al tracking
commit-raw GitHub di `ingest_to_remotedb.all_repos` (`AutobookNft/pinocapasso`,
`florenceegi/le-vespe-cafe`, `florenceegi/os3-matrix`) → ora in `daily_stats`/`daily_detail`.
Per anti-overwrite, i 3 repo NON vanno in `ingest_missions.REPO_TO_DIR` né
`rebuild_all_daily.REPO_TO_DIR` (ricostruiscono da git LOCALE, cloni stale → azzererebbero
i daily GitHub). Documentato come debito "3 liste repo → 1".

## Step 2 — SSOT impattati (diretti)
- `backend/MULTI_REGISTRY.md` — già aggiornato a mano dal CEO. **VERIFICATO**, no_change.
- `README.md` — gap: la riga "Ingestion Dati (ingest_to_remotedb.py)" descrive il componente
  modificato e, per pattern proprio del README (righe sorelle M-220/M-221), deve puntare al
  dettaglio M-222. **ADDITIVE**.

## Step 4 — Discriminazione e modifiche

### backend/MULTI_REGISTRY.md — NO_CHANGE (verificato)
Sezione "Copertura repo nei grafici giornalieri (M-222)" già presente e **semanticamente
corretta**. Verifiche incrociate contro il codice:
- "tracciavano solo 15 repo florenceegi/*" → confermato: `git show HEAD` conta 15 `florenceegi/*`
  pre-esistenti in `all_repos`. ✓
- 3 repo aggiunti solo in `ingest_to_remotedb` → confermato dai 3 diff. ✓
- Anti-overwrite git-locale in `ingest_missions`/`rebuild_all_daily` → confermato dai commenti
  nei rispettivi diff. ✓
- Limite v2 (stats_v2 mission-based, EGI-DOC-only) → coerente con la nota M-220/M-221 esistente. ✓
Copre i 3 punti richiesti dal compito: copertura repo, debito 3-liste, limite grafici v2.
Nessuna modifica necessaria.

### README.md — ADDITIVE (applicata)
Riga "Ingestion Dati (`ingest_to_remotedb.py`)": aggiunta una frase che cita M-222, i 3 repo
del CEO ora tracciati, e rimanda a `backend/MULTI_REGISTRY.md` per copertura/debito/limite v2.
Allineata al pattern delle righe sorelle (M-220 su ingest_missions, M-221 su enrich_by_message),
ciascuna con il proprio pointer al MULTI_REGISTRY. Patch additiva, basso rischio, nessuna
soglia Git Safety superata (1 riga modificata).

## Esaustività (grep)
`grep -rln` su tutti i .md per `le-vespe-cafe|pinocapasso|os3-matrix|daily_stats|grafici giornalieri`
e per `M-222`: gli unici SSOT pertinenti sono README.md e backend/MULTI_REGISTRY.md (entrambi
ora referenziano M-222). `audit/doc_sync/M-221/doc_sync_summary.md` è artefatto storico — non toccato.
`CLAUDE_ECOSYSTEM_CORE.md` escluso per istruzione (modifica estranea/nota).

## Step 5 — RAG
Skip (rag_mode: skipped_no_schema). Nessun re-index, nessun sanity check.

## Step 5b — Metadati registry
Skip: nessun SSOT_REGISTRY.json da aggiornare (verification_mode: registry_only N/A).

## Coverage check (file nuovi)
`backend/tests/m_222_repo_coverage_test.py` (nuovo): test, non doc. Coperto narrativamente da
MULTI_REGISTRY.md (riga "Test" elenca m_220/m_221; il test M-222 è documentato implicitamente
dalla sezione M-222). Informativo, non blocca.

## Esito
- SSOT additivi: 1 (README.md)
- SSOT no_change verificati: 1 (MULTI_REGISTRY.md)
- SSOT sostitutivi: 0
- Approvazioni richieste: 0 (solo additive)
- outcome: success
