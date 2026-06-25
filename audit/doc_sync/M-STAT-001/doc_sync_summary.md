# DOC-SYNC v2 — M-STAT-001

**Data:** 2026-06-25 · **Istanza:** EGI-STAT (`/home/fabio/EGI-STAT`) · **Modalità:** LSO ridotto (no SSOT_REGISTRY documentale, no RAG_SCHEMA)
**Commit:** d09ca8503dabdda6565b66aaa63643625bd4c939 — `[FIX] M-STAT-001 — builder stats.db esporta trigger_matrix + design`

## Cosa è cambiato (Step 1)
Il builder dello `stats.db` esporta due colonne nuove — `trigger_matrix` (INTEGER 1..6 o NULL) e `design` (TEXT 'ok'|'waiver'|NULL) — in **entrambe** le tabelle SQLite `missions` e `missions_open`. `ecosystem.normalize_mission`/`normalize_open_mission` le derivano dal registry (`trigger_matrix` pass-through; `design` da `design_fingerprint`→'ok' / `design_waiver`→'waiver'); `aggregate_to_sqlite.py` le scrive con l'upsert esistente. Speculare al serving M-NEXUS-008. Additivo, conteggi di produzione invariati. **Trigger Matrix: tipo 2** (comportamentale — schema/output cambiato, nessun nuovo endpoint/model).

## SSOT impattati (Step 2 — degradato a scansione manuale esaustiva)
Nessun `docs/lso/SSOT_REGISTRY.json` in questa istanza → scansione grep esaustiva dei doc che descrivono lo schema delle tabelle / la pipeline aggregate.

| SSOT | Posizione | Esito |
|---|---|---|
| `backend/MULTI_REGISTRY.md` | in-instance | **ADDITIVE applicato** |
| `os3-matrix/docs/stats/STATS_SYSTEM_SSOT.md` | cross-organo (fuori instance_root) | **ADDITIVE proposto** (non auto-applicato) |

## Step 3 / 5 — RAG
Skippati: nessun RAG_SCHEMA configurato (modalità LSO ridotto, coerente con M-220/M-221/M-251).

## Modifiche applicate (Step 4)
- **`backend/MULTI_REGISTRY.md`**: esteso l'elenco colonne di `missions_open` (riga 186) con `trigger_matrix, design`; aggiunto blockquote di delta datato `### Campi-scheda dettaglio: trigger_matrix + design (M-STAT-001, ...)` che documenta le 2 colonne su entrambe le tabelle. Diff: `diffs/MULTI_REGISTRY.md.diff`.
  - Esaustività (M-OS3-027): grep di verifica — unica occorrenza dell'elenco-colonne aggiornata. Riga 194 (return dict nel criterio di partizione WIP) lasciata invariata di proposito: descrive il criterio delivered↔open, non lo schema-colonne; i nuovi campi non vi partecipano.
- **`os3-matrix/docs/stats/STATS_SYSTEM_SSOT.md`** (SSOT canonico cross-ecosistema): patch additiva **proposta** in `diffs/STATS_SYSTEM_SSOT.proposed.md`. NON auto-applicata perché fuori da instance_root EGI-STAT (Regole assolute 6 e 9; stesso pattern di M-251 `proposed_external`). **Azione operatore richiesta**: applicare via DOC-SYNC dell'organo os3-matrix o manualmente.

## Step 5b — metadati registry
N/A: nessun SSOT_REGISTRY documentale da aggiornare (modalità `registry_only` non applicabile, registry assente).

## Coverage check (Step 6)
File nuovo della mission: `backend/tests/m_fuc_062_builder_test.py` (test). Nessun watch SSOT lo copre — atteso per i file di test in questa istanza (coerente con `uncovered_new_files` di M-251). Informativo, non blocca.

## Esito
**success.** 1 SSOT in-instance modificato (additive), 1 SSOT cross-organo proposto per l'operatore. 0 sostitutivi, 0 rifiuti, 0 approvazioni richieste.
