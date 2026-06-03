# EGI-STAT multi-registry — M-220

> `mission_stats` aggrega le missioni di **tutti** gli organi dell'ecosistema,
> non solo EGI-DOC. Istituito da M-220 (2026-06-01) dopo il decoupling Oracode Nexus.

> **Aggiornamento M-225 (2026-06-03) — pipeline SQLite, fonte unica.** Il rework stat (SSOT
> `os3-matrix/docs/stats/STATS_SYSTEM_SSOT.md`) introduce `aggregate_to_sqlite.py`: la discovery
> ora usa **SOLO `~/oracode-engine/projects.json`** (il filesystem-walk M-220 descritto sotto è
> **deprecato** come fonte di discovery), e il serving avviene da un **SQLite locale**
> (`backend/data/stats.db`, gitignored) rigenerabile dai JSON registry, con **merge-union
> cross-registry senza perdita di commit_hashes**. Il Postgres `stat.*` (incl. `mission_stats`)
> sarà dismesso (unità S3). Questo doc resta valido per lo storico M-220; per il sistema attuale
> vedi il SSOT STATS.

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

## Enrich per-organo (`enrich_by_message.py`, M-221 fase-2)
Gli organi senza blocco `stats` nel registry (os3-matrix, LeVespe, oracode, …)
sono enrichati attribuendo i commit per **id-missione**: l'id (globalmente unico)
è cercato nel **subject** dei commit di tutti i repo git dell'ecosistema (un pass
`git log` per repo; cross-repo — una missione può toccare più repo). PI calcolato
con la stessa formula di `ingest_missions`. È un **fallback**: dove il registry ha
già `stats` ricche (EGI-DOC enrichato) quelle vincono. Attribuzione **subject-only**
di proposito: un commit il cui subject è di un'altra missione ma che menziona l'id
nel body NON viene attribuito (no cross-reference incidentali).

## Stato e limiti
- **Count: completo.** mission_stats riflette tutti gli organi, taggati.
- **Git-stats (PI): 208/218 reali** (era 150/150 EGI-DOC pre-M-220). I **10 residui
  a PI=0** sono missioni il cui id non compare nel subject di alcun commit
  (convenzione non seguita) o senza codice (parent/coordinamento, audit). Limite
  onesto del metodo, non un bug: nessun commit referenzia l'id → nessuna stat.
- **Attribuzione subject-only vs full-message (debito noto).** `enrich_by_message`
  (organi engine) attribuisce per l'id nel **subject**; il path ricco
  `enrich_registry.py` (EGI-DOC) usa `git --grep` su **tutto il messaggio**
  (subject+body). Una missione è toccata da UN solo path (ricco se disponibile,
  altrimenti fallback) → nessuna doppia attribuzione della stessa missione, ma i
  due gruppi non sono perfettamente confrontabili (es. M-OS3-047: subject 7 vs
  full-message 8). Scelta deliberata (attribuire al lavoro reale del commit, non a
  cross-reference incidentali nel body). Harmonizzazione futura = mission a parte
  (Trigger 6, tocca i numeri di tutti gli organi → approvazione CEO).
- **Commit multi-id**: un commit che cita ≥2 id (es. `[REFACTOR] M-207 + M-208`)
  attribuisce le righe per intero a entrambi → l'aggregato PI di ecosistema
  **sovra-conta** i commit "ponte". Coerente con `enrich_registry.py` (stessa
  convenzione), non una regressione M-221.

## Copertura repo nei grafici giornalieri (M-222)
I grafici **daily/weekly** (vista per-repo, `daily_stats` ← `ingest_to_remotedb.py`
da GitHub API) tracciavano solo 15 repo `florenceegi/*`. M-222 ha aggiunto i repo
del CEO che mancavano: **`AutobookNft/pinocapasso`** (org GitHub diversa),
**`florenceegi/le-vespe-cafe`**, **`florenceegi/os3-matrix`** — ora i loro commit
appaiono in `daily_stats` e nella vista `daily_detail`.

**⚠️ Debito "3 liste repo → 1":** la lista repo è duplicata in 3 file con sorgenti
diverse: `ingest_to_remotedb.all_repos` (GitHub API), `ingest_missions.REPO_TO_DIR`
e `rebuild_all_daily.REPO_TO_DIR` (git LOCALE). I 3 repo nuovi sono **solo** in
`ingest_to_remotedb` (GitHub): NON in `rebuild_all_daily`/`ingest_missions` perché
quei due ricostruiscono da git locale e i cloni sono stale → sovrascriverebbero i
daily GitHub azzerandoli. Vanno unificate in un `repos_config.py` con un flag
"GitHub-only-no-local".

**Limite RISOLTO (M-226, 2026-06-03):** i grafici **v2** della dashboard
(`/api/v2/stats/*`) NON sono piu EGI-DOC-only. `stats_v2` e stato riscritto per leggere
**ESCLUSIVAMENTE** lo **SQLite serving** (`backend/data/stats.db`), che e popolato
**multi-organo** da `aggregate_to_sqlite.py` (discovery via `projects.json`). Non legge piu
`MISSION_REGISTRY.json` ne il Postgres `stat.*`. Le line-chart coprono ora tutti gli organi
(fix *"settimane recenti zero"*).

**Limite RISOLTO (M-229, 2026-06-03):** anche il **resoconto giornaliero** e ora off-Postgres.
`DailyStats.jsx` e stato **riagganciato** da `/api/stats/daily_detail` (v1 Postgres, all-repo) a
`/api/v2/stats/daily_detail` (SQLite **mission-only**, `stats_v2.daily_detail`). Da ora **entrambe** le
viste della dashboard (grafici settimanali/mensili **E** giornaliero) leggono dalla stessa fonte unica
mission-only; zero Postgres nel path dashboard. Il vecchio endpoint v1 Postgres resta **intatto ma non
piu usato dal frontend** (DROP Postgres `stat.*` ancora **GATED** sulla decisione CEO — vedi SSOT STATS
unita 5/8 e `POSTGRES_DECOMMISSION_ANALYSIS.md`).

## Test
`tests/m_220_multiregistry_test.py` — oracle indipendente: rilegge i registry,
conta i completed per-organo, asserisce che il DB combaci (+ colonna/PK `organ`).
`tests/m_221_enrich_by_id_test.py` — oracle eterogeneo (shell `git log --grep`):
su una missione enrichata per-id (es. M-OS3-047) verifica commit/PI reali nel DB
e il calo dei PI=0; attribuzione subject-only come l'impl.
