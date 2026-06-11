# DOC-SYNC v2.2 — M-266 (EGI-STAT)

> Eseguito: 2026-06-11 | Outcome: SUCCESS | RAG: skipped_no_schema (LSO ridotto)
> Modalità: **registry-less degradata** — `docs/lso/SSOT_REGISTRY.json` ASSENTE in EGI-STAT;
> insieme doc candidato fornito esplicitamente dal chiamante mission.

## Mission

M-266 — stat.florenceegi.com: deploy EGI-STAT dietro basic auth + endpoint pubblico
`/api/public/site-stats` per fabiocherici.com. Nuovi: `backend/public_stats.py`,
route + after_request split in `backend/api.py` (R1 assorbita), stack deploy completo
(`deploy/nginx/stat.florenceegi.com.conf`, `deploy/systemd/egi-stat.service`,
`deploy/deploy-stat.sh`, `deploy/push-stats.sh`), DNS Route53, test `tests/m-266/`.

## SSOT processati

| Doc | Modo | Esito |
|---|---|---|
| `backend/MULTI_REGISTRY.md` | additive | APPLIED — nuova sezione "Endpoint pubblico aggregato — /api/public/site-stats (M-266)" prima di ## Test (consumer del serving SQLite, vincolo privacy, difese R1, rate-limit nginx) |
| `backend/TIME_ENTRIES_FORMAT.md` | additive | APPLIED — §Serving: paragrafo sul secondo consumer pubblico di `time_entries` (solo totali, mai nomi) |
| `README.md` | additive | APPLIED — nuova sezione "Deploy corrente — stat.florenceegi.com (M-266)"; annotazione header sezione Forge → "(legacy — superato da M-266)" **da ratificare dall'operatore** (contenuto legacy intatto) |
| `CLAUDE.md` | no_change | Già aggiornato DENTRO la mission (R2): verificato coerente col codice, nessun intervento |

Non impattati: `frontend/README.md` (nessun riferimento a serving/deploy backend),
`backend/POSTGRES_DECOMMISSION_ANALYSIS.md` (analisi storica, stato invariato).
Laterale fuori-repo: `EGI-DOC/ROUTE53_SUBDOMAIN_PROCEDURE.md` già aggiornato/pushato in altra sede.

## Verifica esaustività (M-OS3-027)

- `grep "non deployato"` → 0 occorrenze residue (claim vecchio rimosso ovunque).
- Ogni doc modificato cita ora `site-stats`.
- **Residui registrati (non bloccanti, fuori scope M-266 — anti-pattern 9):** README righe
  15/38/56 citano PostgreSQL per la pipeline ingestion v1 (legacy ma esistente) — staleness
  pre-esistente; candidata a futura mission di rewrite README.

## Coverage check (regola 8 — informativo)

File nuovi della mission (`backend/public_stats.py`, `deploy/*`, `tests/m-266/*`) NON coperti
da alcun watch: `SSOT_REGISTRY.json` non esiste in questo organo. Triage suggerito: istituire
`docs/lso/SSOT_REGISTRY.json` con watch su `backend/*.py` → `backend/MULTI_REGISTRY.md` e
`deploy/**` → `README.md` §Deploy corrente.

## Registry

Entry M-266 in `docs/missions/MISSION_REGISTRY.json` aggiornata: `doc_sync_executed: true`,
`doc_sync_outcome: success`, contatori, `doc_sync_audit_path`, `doc_verified: true (2026-06-11)`.
