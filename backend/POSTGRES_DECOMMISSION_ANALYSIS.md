# Postgres `stat.*` → SQLite — Complete Flow Analysis (M-227 / S3)

> P0-8 Complete Flow Analysis prima di spegnere Postgres (SSOT STATS Parte 2 §Migrazione).
> Esito: `stat.*` è **isolato a EGI-STAT** (zero dipendenze cross-organo). La dismissione è sicura
> TRANNE per UN consumatore che richiede una **decisione CEO**. Drop **gated** (script pronto, non eseguito).

## Scrittori Postgres `stat.*` (cron `daily_ingest.sh`)
| File | Tabella | Note |
|---|---|---|
| `ingest_to_remotedb.py:167-315` | `stat.commits`, `stat.daily_stats`, `stat.weekly_stats` | **TUTTI** i commit dei 18 repo via GitHub API (all-repo, non-mission) |
| `ingest_missions.py:289-436` | `stat.daily_stats`, `stat.weekly_stats`, `stat.mission_stats` | mission-scoped → **ridondante** (SQLite lo copre da M-225/226) |

## Lettori Postgres `stat.*`
| Endpoint (api.py) | Tabella | Consumatore frontend | Migrabilità a SQLite |
|---|---|---|---|
| `/api/stats/daily_detail` (74-161) | `stat.daily_stats` | **`DailyStats.jsx:18` (ATTIVO)** | **(c) NO** — richiede dati all-repo non presenti in SQLite |
| `/api/stats/weekly` (38-72) | `stat.weekly_stats` | nessuno | (a) as-is |
| `/api/stats/missions` (181-254) | `stat.mission_stats` | nessuno | (a) as-is (dati già in SQLite) |
| `/api/stats/mission_timeline` (257-289) | `stat.mission_stats` | nessuno | (a) as-is |
| `/api/raw_commits` (162-179) | `stat.commits` | nessuno | (b) estendere ingest SQLite |
| `/api/v2/stats/*` | — | App.jsx | già SQLite (S2), Postgres-free |

## GAP dati decisivo
`stat.daily_stats` (Postgres) = **tutti** i commit per-repo-per-giorno (GitHub API, anche repo non-mission:
le-vespe-cafe, pinocapasso, …). `mission_repo_day` (SQLite) = **solo** commit attribuiti a missioni chiuse.
→ `daily_detail` / `DailyStats.jsx` (Daily Snapshot all-repo) **non è ricostruibile** dal SQLite attuale.

## DECISIONE CEO RICHIESTA (gate)
> **Il prodotto Oracode-STAT necessita dello snapshot giornaliero ALL-REPO (commit non legati a mission),
> o è sufficiente la vista mission-scoped (v2)?**

- **Se SUFFICIENTE mission-scoped** → rimuovi `DailyStats.jsx` + endpoint v1, esegui `migrations/drop_stat_schema.sql`,
  disattiva entrambi gli ingest Postgres. Pipeline 100% SQLite.
- **Se SERVE all-repo** → estendi l'aggregatore/SQLite con una tabella `repo_day` all-repo (ingest da
  git/GitHub, NON solo mission) e migra `daily_detail` a quella; poi spegni Postgres. (Schema enhancement.)

## Cosa è REVERSIBILE e sicuro SUBITO (indipendente dalla decisione)
- L'ingest **mission-scoped** verso Postgres (`ingest_missions.py` → `stat.mission_stats`/`daily_stats`/`weekly_stats`)
  è **ridondante** (SQLite lo copre): disattivabile in `daily_ingest.sh` commentando, **reversibile**.
- L'ingest **all-repo** (`ingest_to_remotedb.py`) va **tenuto acceso** finché la decisione non è presa
  (alimenta `daily_detail`).
- `migrations/drop_stat_schema.sql`: **pronto, NON eseguito** (boundary: nessun DROP autonomo).

## Connettività
Postgres `stat.*` letto/scritto SOLO da EGI-STAT. `EGI-DOC/pipeline` usa `rag_natan` (schema diverso, non-stat).
Nessun altro organo tocca `stat.*`.

---
*Complete Flow Analysis M-227 — 2026-06-03. Decommission EXECUTION gated sulla decisione CEO sopra.*
