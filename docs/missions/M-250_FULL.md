# M-250 — Rebuild stats.db atomico (esteso)

> Report esteso (FASE 6a). Tecnico: M-250.md.

## Contesto e responsabilità
Il CEO ha segnalato che la dashboard, **corretta ~2 ore prima**, mostrava di nuovo le metriche mission-derived a zero, e ha ordinato di NON dedurre ma di far analizzare DeepDebug. La regressione è stata introdotta da me con M-247 (`ensure_fresh` on-read) e innescata dal re-enrich globale.

## Diagnosi (DeepDebug + riproduzione deterministica)
- `stats_v2._connect()` (M-247) chiama `_ensure_fresh()` ad OGNI lettura. `ensure_fresh` ricostruisce se `is_stale` (un registry più recente del DB).
- Il **re-enrich globale** ha riscritto i `MISSION_REGISTRY.json` di tutti gli organi → mtime = "ora" → DB perennemente `is_stale` finché non rigenerato.
- `aggregate()` apriva il DB **servito** e faceva `create_schema` = `DROP TABLE`+`CREATE` su `missions`/`mission_repo_day`/`mission_tags`/`mission_organs`. Sotto Flask `debug=True` (2 worker) + richieste concorrenti, un lettore poteva colpire il DB **dopo il DROP e prima del repopulate** → `missions=0`.
- Le tabelle `legacy_repo_day`/`legacy_production`/`time_entries` (righe, file, ore) erano popolate in fasi diverse → spiegano lo **split selettivo**: mission-derived a 0, lavoro/ore popolati.
- **Riproduzione**: `touch <registry>` (stale) + 10 `curl` parallele → 7/10 con `missions=0`, alcune con 114 settimane (DB parziale). Deterministico.

## Fix — rebuild atomico
`aggregate(db_path)`:
- costruisce su `tmp = <db_path>.building.<pid>` (sqlite separato);
- a fine build fa **`os.replace(tmp, db_path)`** — rename atomico sullo stesso filesystem: un lettore apre sempre l'inode completo (vecchio o nuovo), mai uno a metà;
- **guard**: se `n_missions==0` e `len(registries)==0` (discovery vuota) NON sovrascrive il DB valido esistente (meglio dati vecchi che vuoti).

## Verifica
- `tests/m_250_atomic_rebuild_test.py`: un thread lettore legge `COUNT(*) FROM missions` mentre `aggregate()` gira 3 volte; asserisce che non veda MAI 0 / 'no such table'. RED prima (DROP+CREATE non atomico), GREEN dopo.
- Stress reale: stale + 10 `curl` parallele → **10/10 = 168** (prima 7/10 a 0).
- Regressione completa: 20/20. Servizio `egi-stat-api.service` riavviato.

## Nota
La combinazione corretta ora: `ensure_fresh` mantiene il serving allineato ai registry (M-247) MA il rebuild è atomico (M-250) → freschezza senza race. Per produzione pura si potrebbe anche passare `debug=False` (un solo worker) — non necessario col fix atomico.
