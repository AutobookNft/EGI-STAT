# EGI-STAT multi-registry — M-220

> `mission_stats` aggrega le missioni di **tutti** gli organi dell'ecosistema,
> non solo EGI-DOC. Istituito da M-220 (2026-06-01) dopo il decoupling Oracode Nexus.

## Perché
Prima del decoupling, tutte le missioni vivevano nel registry di EGI-DOC.
Il decoupling ha creato registry **per-organo** (os3-matrix, oracode, Capasso,
LeVespe, fabiocherici, Poli, …). `ingest_missions.py` puntava a un solo path
hardcoded → EGI-STAT vedeva ~150/289 missioni. Ora le scopre tutte.

## Come

### Discovery (`ecosystem.py`)
`discover_registries()` = UNION di:
1. **`oracode-engine/projects.json`** — censimento engine (cattura progetti
   fuori dai root di scan, es. Poli in `/tmp/oracode`).
2. **walk filesystem** di `SCAN_ROOTS` (`/home/fabio`, `/tmp/oracode`) con
   pruning (`node_modules`, `.git`, …) — cattura i registry non engine-registered
   (fabiocherici, ORACODE-DOC, archive).

Dedup per realpath. `organ` = basename della dir-progetto. Tutti i repo contano
(Poli e archive inclusi — decisione CEO: sono produzione).

### Normalizzazione 2-schemi (`ecosystem.normalize_mission`)
Due schemi coesistono nei registry:

| campo | legacy-IT (EGI-DOC) | engine-EN (os3-matrix engine) |
|---|---|---|
| id | `mission_id` | `id` |
| stato-completo | `stato == "completed"` | `status == "closed"` |
| titolo | `titolo` | `title` |
| date | `data_apertura` / `data_chiusura` | `date_open` / `date_close` |
| git-stats | blocco `stats{}` | **assente** |

`normalize_mission` mappa entrambi a un canonico; ritorna `None` per le missioni
non completate o senza id (saltate).

### Schema DB (`migrate_mission_stats_organ.py`, idempotente)
- `mission_stats.organ` (text, NOT NULL) — l'organo di provenienza.
- PK → **`(organ, mission_id)`**: missioni con lo stesso id in organi diversi
  (es. `oracode` M-001 vs `EGI-DOC` M-001) non collidono.
- `mission_id` / `mission_type` allargati a `text` (id come `M-094-SUPERVISOR`).

## Stato e limiti
- **Count: completo.** mission_stats riflette tutti gli organi, taggati.
- **Git-stats (PI): parziale.** 93/217 righe a PI=0. Due cause: (a) gli organi
  mai enrichati (os3-matrix, LeVespe, …) — `enrich_registry.py` enricha solo
  EGI-DOC (organ-map interna); (b) anche **EGI-DOC** ha ~45 missioni a PI=0
  (audit/doc senza commit git mappabili). → **fase-2**: generalizzare l'enrich
  con una repo-map per-organo (i descrittori `.oracode/project.json` espongono
  `repo_map_path`).

## Test
`tests/m_220_multiregistry_test.py` — oracle indipendente: rilegge i registry,
conta i completed per-organo, asserisce che il DB combaci (+ colonna/PK `organ`).
