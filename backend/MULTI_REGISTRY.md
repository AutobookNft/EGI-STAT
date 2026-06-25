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

## Asse ORE — tabella `time_entries` + endpoint hours (M-234, 2026-06-03)
`aggregate_to_sqlite.py` aggiunge una **6a tabella** allo schema SQLite serving:
**`time_entries`** (`id, project, mission_id, date, source, description, minutes`;
`CHECK source IN ('manual','commit')`, `CHECK minutes >= 0`; indici su `project` e
`source`). È l'**asse ore** (tempo), distinto dall'asse *commit* (produzione) — tabella
separata, mai sommata ai `weighted_commits`. Due sorgenti:
- **`manual`** — dato reale CEO da `<instance_root>/docs/missions/TIME_ENTRIES.json`
  (`load_time_entries_manual`), `project` preso dalla voce, `mission_id` =
  `ledger_mission` (registri perpetui M-OS3-058; nessuna FK perché `M-LEDGER-*` non è
  in `missions`).
- **`commit`** — stima-euristica (`estimate_commit_minutes`) sui timestamp dei **SOLI
  commit-mission** (esclusività mission): clustering **per repo**, `SESSION_GAP_MIN=90`
  (gap > 90 min → nuova sessione), `PRE_SESSION_MIN=30`. **Attribuzione per REPO reale**
  (fix M-239): il `project` della riga è il **repo reale** dove vive il commit (`github_repo`
  normalizzato a basename: `florenceegi/EGI-DOC`→`EGI-DOC`, `AutobookNft/pinocapasso`→`pinocapasso`),
  **NON** l'organo scalare della mission. 1 riga per **(repo, sessione)**, `minutes = span + PRE_SESSION_MIN`
  (niente split per-project, no doppio conteggio).

Serving: `stats_v2.hours_by_project()` → `SUM(minutes) GROUP BY project` con
`manual_minutes`/`commit_minutes` **espliciti** (P0-3; la stima non si presenta mai come
ore reali), esposto da **`GET /api/v2/stats/hours`**. Meta: `time_entries_manual` /
`time_entries_commit`. Primo dato reale: **Capasso** 300 min (incontro Stefania) +
stima-commit.

### Lato-scrittura asse ORE (M-237, 2026-06-03)
M-234 era **sola lettura**. M-237 aggiunge il lato-scrittura delle ore `manual`:
- **`POST /api/v2/stats/time_entries`** (`api.py` → `time_entries_write.py`): valida il payload
  (`project` **whitelisted** da `~/oracode-engine/projects.json` — anti path-traversal; `date` ISO reale via
  `date.fromisoformat`; `minutes` int > 0, `bool` escluso; `description` non vuota), **appende in modo
  atomico** (tmp + `os.replace`, nessuna shell/interpolazione) al `TIME_ENTRIES.json` dell'**istanza**
  risolta dalla whitelist, poi **rigenera l'SQLite serving in-process** (`aggregate()`, no subprocess) →
  la voce compare subito in `GET /api/v2/stats/hours`. Validazione fallita → **400 senza scrittura**
  (UEM-first; mai 500 su input utente). Esito → **201** con la voce scritta.
- **Modale React "Aggiungi tempo"** (`frontend/src/components/AddTimeModal.jsx`, montato in `App.jsx`):
  pannello *Ore per progetto* (legge `GET /hours`) con pulsante **+ Aggiungi tempo** (progetto da select
  whitelist, data, durata ore+minuti → `minutes`, descrizione) → POST → on-success ricarica le ore.

Le voci scritte via endpoint sono identiche a quelle inserite a mano nel file: `source: "manual"`,
`ledger_mission: "M-LEDGER-<PROJECT>"`. Contratto file: vedi `TIME_ENTRIES_FORMAT.md`.

### Stima-commit per REPO reale — vista piatta (M-239, 2026-06-03)
La versione M-234 di `estimate_commit_minutes` attribuiva i minuti all'**organo scalare** della mission,
mappato a `descriptor.project` via `project_of_organ`. Per le ~170 missioni FlorenceEGI l'organo scalare
valeva **sempre** `EGI-DOC`→`FlorenceEGI` → tutti gli organi schiacciati in un lump `FlorenceEGI`,
`le-vespe-cafe` **perso**. Fix M-239: l'attribuzione è per **REPO reale** (`github_repo` normalizzato a
basename), **vista piatta per-repo** (scelta CEO) — `EGI-DOC` è **uno** dei 17 organi/progetti, non
l'ecosistema; `le-vespe-cafe` presente. 1 riga `time_entries` per **(repo, sessione)**, niente split
per-project. Rimosso il codice morto (`project_of_organ`, query `organ_of_hash`, organo nelle tuple →
`commits`/`sessions` = `list[datetime]`; Pilastro 2). Totale stima-commit **invariato** (21455 min):
cambia la ripartizione, non il monte-ore. Test: `EGI-DOC/docs/tests/m-239/test_hours_per_repo.sh`.

### Endpoint pubblico aggregato — `/api/public/site-stats` (M-266, 2026-06-11)
Primo (e unico) endpoint **senza basic auth** del deploy `stat.florenceegi.com`: alimenta il
widget "cantiere aperto" di fabiocherici.com. `backend/public_stats.py::site_stats()` legge lo
**stesso SQLite serving** di stats_v2 (`stats_v2._connect`, `_CLOSED_WHERE`) e restituisce **SOLO
totali**: `hours_total` / `hours_last_7_days` (da `time_entries`, con `hours_note:
"manual + commit-estimate"` — onestà epistemica P0-3), `projects_total` / `projects_active_30d`
(COUNT DISTINCT), `lines_net_total` (mission chiuse + `legacy_production` M-OS3-086, tabella
assente tollerata), `last_activity`, `generated_at`. **Vincolo privacy (by design): MAI nomi
progetto/mission** — il dettaglio resta nella dashboard dietro basic auth.

Difese (audit M-266 R1): in `api.py` l'`after_request` è **split** — `/api/public/*` riceve
`Cache-Control: public, max-age=60` **solo su status 200** (errori `no-store`),
`Access-Control-Allow-Origin: https://fabiocherici.com` + `Vary: Origin`; il resto di `/api/`
resta no-store. Errori dell'endpoint → risposta **generica** `{"error": "stats unavailable"}`
(dettaglio solo nel log server-side). Lato nginx (`deploy/nginx/stat.florenceegi.com.conf`):
`location /api/public/` con `auth_basic off` + rate-limit `10r/m` burst 20.
Test: `tests/m-266/test_public_site_stats.sh`.

## Mission IN CORSO — tabella `missions_open` + endpoint (M-FUC-054, 2026-06-16, ADDITIVO)
Accanto alle mission **delivered** (tabella `missions`, asse produzione) il serving espone ora le mission
**IN CORSO** (WIP) per il cockpit Nexus. `aggregate_to_sqlite.py` aggiunge una **tabella additiva**
**`missions_open`** (`id, organ, title, raw_status, mission_type, date_opened, trigger_matrix, design,
discovered_at`; PK `(organ, id)`; indici su `organ` e `raw_status`), popolata da un **Pass DEDICATO** (dopo
Pass1/Pass2) che ri-scorre **gli stessi** registry via `insert_open_mission` → `ecosystem.normalize_open_mission`. Path
**completamente separato** da `insert_mission`/`normalize_mission`: NON scrive in `missions` né nelle sue
child-table → **conteggi prod identici** (vincolo CEO). Nessuna chiamata git (O(mission)). In `DROP_TABLES`
(full-rebuild ricostruisce anche questa). Meta: `missions_open_count`.

**Chi è "in corso" (partizione disgiunta da `missions`, anti-doppio-conteggio H3).** `normalize_open_mission`
ritorna `{id, title, raw_status, date_opened, mission_type}` SSE: la mission ha un `id`; ha uno `status`
engine-EN con **`status_is_open(status)`** True (presente in `MISSION_STATUS_TAXONOMY` con `terminal==false
AND counts_as_production==false`, **escluso `perpetual`** = registro non-chiudibile, non WIP); e **NON** è
delivered. La regola *delivered* è stata **estratta** in **`ecosystem._is_delivered(m)`** (data di chiusura
valida — non `None`/`""`/`"pending"`, su entrambi gli schemi `data_chiusura`/`date_close`) e **condivisa** tra
`normalize_mission` (prod) e `normalize_open_mission` (WIP) — refactor **neutro** così i due path **non possono
divergere** sul confine delivered↔open. Registry **legacy-IT senza `status` engine** → None (non hanno lo
status-engine che distingue draft/executing/auditing). **Loud-on-unknown** coerente con
`status_counts_as_production`: status fuori-tassonomia → warning stderr + `False` (mai sparizione silenziosa,
M-OS3-090). Verificato: **496 delivered / 28 open / 0 intersezione**.

Serving: **`stats_v2.open_missions()`** legge SOLO `missions_open`, ordine **esplicito** (P0-3)
`date_opened DESC, organ, id`, shape per il cockpit `[{mission_id, organ, title, status, mission_type,
date_opened}]` (mapping `raw_status→status`, `id→mission_id`), esposto da
**`GET /api/v2/stats/missions_open`** (`api.py::get_v2_missions_open`, stesso pattern try/except degli
endpoint v2). **Confine** (Pilastro 3): è una vista aggiuntiva di lettura (mission *non ancora* produzione),
mai sommata ai `weighted_commits`, fuori da `_CLOSED_WHERE` e dalla time-series. Test P0-13
`tests/m_fuc_054_open_missions_test.py` **13/13 GREEN** (7 nuovi + 6 invariante m_248). SSOT canonico:
`os3-matrix/docs/stats/STATS_SYSTEM_SSOT.md` §Mission IN CORSO.

### Campi-scheda dettaglio: `trigger_matrix` + `design` (M-STAT-001, 2026-06-25, ADDITIVO)
Il builder esporta ora due colonne aggiuntive **in entrambe** le tabelle `missions` e `missions_open`:
**`trigger_matrix`** (INTEGER, `1..6` dalla Trigger Matrix DOC-SYNC, o `NULL`) e **`design`** (TEXT,
`'ok'|'waiver'|NULL`, governance del design gate). `ecosystem.normalize_mission`/`normalize_open_mission`
le derivano dal registry: `trigger_matrix` passa-attraverso da `m['trigger_matrix']`; `design` mappa
`design_fingerprint → 'ok'`, `design_waiver → 'waiver'`, altrimenti `None`. `aggregate_to_sqlite.py`
(`insert_mission`/`insert_open_mission`) le scrive col medesimo upsert `ON CONFLICT(organ,id) DO UPDATE`.
**Confine** (Pilastro 3, additivo): nuove colonne nullable, nessuna metrica di produzione tocca questi
campi, conteggi e time-series invariati. **Speculare al serving M-NEXUS-008**: il cockpit serve i 3
campi-scheda (`trigger_matrix`, `design` + titolo) dal **medesimo SQLite** della lista, non più da
`bin/mission show` (che sul box leggeva file-registry stali coi path del laptop). Test:
`tests/m_fuc_062_builder_test.py` **4/4**. SSOT canonico: `os3-matrix/docs/stats/STATS_SYSTEM_SSOT.md`
§Mission IN CORSO (patch additiva proposta, cross-organo — vedi audit `M-STAT-001`).

## Copertura di INSTRUMENTAZIONE dei repo — scanner ship-with-push (M-FUC-057, 2026-06-16, ADDITIVO)
> Distinto dalla "Copertura repo nei grafici giornalieri" (M-222, sopra): qui si misura **quali repo git sono
> instrumentati** per le stat, non i dati per-giorno. La discovery delle stat vede solo i repo in
> `~/oracode-engine/projects.json`; un repo git **senza** `.oracode/project.json` è invisibile.
>
> **`backend/coverage_scan.py`** (NUOVO) fa il walk dei repo git sotto `COVERAGE_SCAN_ROOT` (default `~`, salta
> dotdir) e li confronta con `projects.json` + i descrittori, classificando: **`instrumented`** (descrittore + in
> projects.json), **`orphan_descriptor`** (ha descrittore ma NON in projects.json → mission non contate finché non
> si apre una mission da lì), **`uninstrumented`** (git senza descrittore → fuori dalle stat), **`index_pollution`**
> (voci projects.json con root `/tmp` o inesistente → drift dell'indice da bonificare). Output `data/coverage.json`
> (o `--print` su stdout). Campi: `generated_at`, `instrumented`, `uninstrumented`, `orphan_descriptor`,
> `index_pollution` (liste).
>
> **Vincolo topologico (REGOLA ZERO).** I repo vivono sul **laptop**; il cockpit gira sul **server** EC2 che non
> li ha → scan server-side = falsa. Quindi **ship-with-push**: la scansione gira sul laptop e `coverage.json`
> viaggia col push stat esistente. **`deploy/push-stats-nexus.sh`** (MODIFICATO): step **1b** genera `coverage.json`
> + step **2b** `s3 cp`; il pull SSM lo tira giù sul server. **Best-effort, event-driven (open/close), NESSUN cron.**
> Il cockpit (`nexus-cockpit`) lo legge via `cockpit_reads.coverage()` + `GET /api/cockpit/coverage` con
> `partial:true` se non ancora arrivato (no falso-verde). Risultato reale M-FUC-057: **16 uninstrumented / 1 orphan
> (`nexus-cockpit`) / 3 index_pollution (TESTPROJ)**. Test P0-13 `tests/M-FUC-057/coverage-ship.test.sh` (in Fucina)
> GREEN 5/5. SSOT canonico: `os3-matrix/docs/stats/STATS_SYSTEM_SSOT.md` §Copertura.

## Test
`tests/m_220_multiregistry_test.py` — oracle indipendente: rilegge i registry,
conta i completed per-organo, asserisce che il DB combaci (+ colonna/PK `organ`).
`tests/m_221_enrich_by_id_test.py` — oracle eterogeneo (shell `git log --grep`):
su una missione enrichata per-id (es. M-OS3-047) verifica commit/PI reali nel DB
e il calo dei PI=0; attribuzione subject-only come l'impl.
