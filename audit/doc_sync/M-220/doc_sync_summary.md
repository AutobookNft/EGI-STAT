# DOC-SYNC v2.2.0 — M-220 (EGI-STAT multi-registry)

> instance_root: `/home/fabio/EGI-STAT`
> Modalita: **LSO ridotto** (no SSOT_REGISTRY.json, no RAG_SCHEMA) → Step 3 e Step 5 skip.
> Trigger Matrix: **Tipo 3 — Architetturale** (nuovo modulo `ecosystem.py`, aggregazione cross-organo, cambio PK DB).

## Cosa e cambiato (M-220)
`ingest_missions.py` reso multi-registry: `mission_stats` ora aggrega le missioni di TUTTI gli
organi dell'ecosistema (non solo EGI-DOC), taggando ogni riga con l'`organ`, normalizzando i due
schemi coesistenti (legacy-IT + engine-EN). Nuovi moduli `ecosystem.py` (discovery + normalize) e
`migrate_mission_stats_organ.py` (migrazione idempotente: colonna `organ`, PK `(organ, mission_id)`,
text-widening). `init_remote_db.py` e `api.py` allineati allo schema.

## SSOT sincronizzati

| SSOT | Mode | Status | Note |
|------|------|--------|------|
| `README.md` | additive | applied | 2 righe additive: responsabilita `mission_stats` multi-organo + modulo `ingest_missions.py`/`ecosystem.py` con pointer a `MULTI_REGISTRY.md` |
| `backend/MULTI_REGISTRY.md` | no_change | no_change | Doc tecnica scritta dalla mission, gia completa e coerente col diff codice |
| `CLAUDE.md` | no_change | no_change | Contesto generico, nessuna claim sul registry/ingestione |

## Cosa era gia coperto
`backend/MULTI_REGISTRY.md` (nuovo, scritto dalla mission) e l'SSOT tecnico completo del cambiamento:
documenta discovery, normalizzazione 2-schemi (tabella campi), schema/PK DB, stato e limiti
(git-stats PI parziale → fase-2 enrich per-organo), e il test oracle. Verificato coerente col
diff di `ecosystem.py`, `migrate_mission_stats_organ.py`, `ingest_missions.py`, `init_remote_db.py`,
`api.py`. Nessuna modifica necessaria.

## README — verifica residui (Step 4.4 esaustivita)
`grep -i "solo EGI-DOC|un solo registry|mono.registry|single registry" README.md` → nessun residuo.
README non descriveva il sistema come mono-registry: semplicemente non copriva il subsystem
`mission_stats`. Patch quindi **additiva**, non sostitutiva. (`single-page application` a riga 18 e
riferito al frontend, non ai registry → lasciato intatto, legittimo.)

## Fuori scope (non toccato — Regola 6 / anti-pattern 9)
- `CLAUDE_ECOSYSTEM_CORE.md`: risulta modificato nel working-tree, ma il diff e una
  **compaction/rewrite generica** del core ecosistema, **senza alcun contenuto M-220**
  (nessun riferimento a `mission_stats`, multi-registry, `ecosystem.py`, tagging organi).
  Change estranea alla mission → non parte del doc-sync M-220, lasciata invariata.
- `.claude/commands/calc-stat.md` e `.claude/commands/mission.md`: skill fuori da instance_root.

## Step eseguiti
Step 1 (semantica), Step 2 (impatti diretti — per ispezione, no registry), Step 4 (discriminazione +
patch additive README), Step 6 (audit). Step 3 e Step 5 skip (LSO ridotto). Step 5b: SSOT_REGISTRY
assente → nessun metadato da aggiornare.
