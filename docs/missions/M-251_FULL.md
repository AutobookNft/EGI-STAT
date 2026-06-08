# M-251 — Rebuild preserva legacy + totali (esteso)

> Report esteso (FASE 6a). Tecnico: M-251.md.

## Diagnosi (DeepDebug, misurata alla fonte)
La colonna "Righe nette" della tabella Ore-per-Progetto (`stats_v2.hours_by_project`) somma DUE sorgenti: `net_mission` (da `missions.lines_net`, dai registry) + `net_legacy` (da `legacy_production`). La massa storica (es. EGI ~696k) viene da `legacy_production`.

`legacy_production`/`legacy_repo_day` sono popolate SOLO da `ingest_legacy_production.py` (ingest separato, `git rev-list`), NON da `aggregate()`. Non sono in `DROP_TABLES`. Misurato: dopo il rebuild atomico M-250, `legacy_production` ASSENTE dal DB (`sqlite_master` non la elenca) → net_legacy=0 per tutti → righe nette crollate.

Causa: M-250 (rebuild atomico) costruiva un DB **nuovo da zero** su file temp e lo sostituiva. Il vecchio rebuild in-place faceva solo DROP delle tabelle elencate (mission/time), lasciando intatte le legacy nello stesso file. Il nuovo file partiva vuoto → legacy perse al primo rebuild atomico.

Confermato anche un danno secondario dal re-enrich `--force`: mission schema-EN (`id: M-EGI-249`) hanno `stats.lines_net=0` perché `git_log_by_mission_id` cerca `M-EGI-249` ma i commit usano `M-249` → grep vuoto → azzeramento. (Misurato: `git log --grep=M-EGI-249` = 0 risultati; tutte le M-EGI-* a 0.) È minoritario rispetto alla massa legacy.

## Fix
`aggregate_to_sqlite.aggregate()`:
- prima del rebuild, se `db_path` esiste, **copia** il DB su `tmp_path` (`shutil.copy2`);
- `create_schema(conn)` droppa/ricrea SOLO `DROP_TABLES` (mission/time/meta) → `legacy_production`/`legacy_repo_day` (non elencate) **sopravvivono** nella copia;
- build + `os.replace` atomico come M-250.
Così le tabelle non gestite da aggregate persistono attraverso ogni rebuild.

Re-ingest: `python3 ingest_legacy_production.py` (quadratura OK) ha ripristinato i dati persi.

## Recupero (verificato)
- `legacy_production` presente; EGI 720.438, EGI-DOC 331.588, NATAN_LOC 222.071.
- Endpoint `/api/v2/stats/hours`: EGI lines_net 741.395; TOTALE righe nette 2.087.976; TOTALE ore 2.162,91.

## Totali tabella (richiesta CEO)
`AddTimeModal.jsx`: aggiunto `<tfoot>` con riga **TOTALE** (somma ore, min. manuali, min. stima-commit, righe nette) quando ci sono progetti.

## Test
`tests/m_251_preserve_legacy_test.py`: crea `legacy_production`, esegue un rebuild, verifica che la tabella e i valori sopravvivano. RED prima (rebuild da zero), GREEN dopo (copia). Regressione 21/21.

## Residuo (secondario, non bloccante)
Le mission schema-EN azzerate dal re-enrich vanno ripristinate via `git restore` dei rispettivi registry alla revisione pre-re-enrich (cross-repo, approvazione CEO), + patch a `enrich_registry.py::git_log_by_mission_id` per cercare anche il tag numerico senza prefisso organo (impedisce ricadute). La massa principale (legacy) è già recuperata.
