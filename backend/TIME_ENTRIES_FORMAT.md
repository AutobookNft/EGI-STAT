# TIME_ENTRIES.json — formato dell'asse ORE (M-234)

> Contratto del file `<instance_root>/docs/missions/TIME_ENTRIES.json`, sorgente delle voci
> di tempo **manuali** (dato reale CEO) dell'asse ORE. Caricato da
> `aggregate_to_sqlite.py::load_time_entries_manual` nella tabella SQLite `time_entries`.
> Istituito da M-234 (2026-06-03). Schema/serving: vedi `MULTI_REGISTRY.md` §Asse ORE e
> il SSOT STATS (`os3-matrix/docs/stats/STATS_SYSTEM_SSOT.md`).

## Perché esiste
L'asse ORE traccia il **tempo** (anche lavoro non-commit), distinto dall'asse *commit*
(produzione). Il tempo non-commit — incontri, telefonate, analisi — non lascia traccia in
git: lo registra il CEO a mano in questo file, attribuito a un **registro perpetuo**
(mission-ledger, M-OS3-058). La stima sui commit la calcola invece l'aggregatore
(`estimate_commit_minutes`), NON questo file.

## Posizione
Un file **per istanza**, opzionale: `<instance_root>/docs/missions/TIME_ENTRIES.json`.
Istanza senza file → 0 voci manuali (NON è un errore). L'aggregatore scopre le istanze dai
descrittori `~/oracode-engine/projects.json`.

## Schema
```json
{
  "entries": [
    {
      "ledger_mission": "M-LEDGER-CAPASSO",
      "project": "Capasso",
      "date": "2026-06-03",
      "source": "manual",
      "description": "incontro Stefania",
      "minutes": 300
    }
  ]
}
```

| campo | obbligo | tipo | semantica |
|---|---|---|---|
| `ledger_mission` | opz. | string | id del registro perpetuo (M-LEDGER-*); finisce in `time_entries.mission_id`. Nessuna FK: i ledger non sono in `missions` |
| `project` | sì | string | nome progetto = chiave di aggregazione delle ore. Fallback al nome progetto del descrittore se assente |
| `date` | opz. | string ISO `YYYY-MM-DD` | data della voce |
| `source` | sì | `"manual"` | SOLO `manual` è accettato qui. Voci con altro `source` (es. `commit`) sono **ignorate** dal loader: le ore-commit le stima l'aggregatore |
| `description` | opz. | string | testo libero |
| `minutes` | sì | int ≥ 0 | minuti. Voci con `minutes <= 0` o senza `project` vengono saltate |

## Regole (P0-3 — parametri statistici espliciti)
- **`source` separato**: `manual` (questo file) e `commit` (stima) non si mescolano mai.
  Il serving (`hours_by_project()`) li espone distinti (`manual_minutes` /
  `commit_minutes`) — la stima non va MAI presentata come ore reali.
- **Idempotente**: la tabella `time_entries` è DROP+CREATE a ogni aggregazione; ricaricare
  il file non duplica.
- **Asse separato dalla produzione**: queste ore NON entrano nei `weighted_commits` né in
  alcuna metrica di produzione mission.

## Inserimento voci (M-237)
Le voci `manual` si aggiungono in **due modi equivalenti**:
- **Edit manuale del file** — il CEO scrive direttamente questo `TIME_ENTRIES.json` (modo originario M-234).
- **Modale "Aggiungi tempo" → endpoint POST** — la dashboard espone il pannello *Ore per progetto* con
  il pulsante **+ Aggiungi tempo** (`AddTimeModal.jsx`); il salvataggio fa `POST /api/v2/stats/time_entries`
  (handler `time_entries_write.py`). Il backend **valida** il payload (`project` whitelisted da
  `~/oracode-engine/projects.json` → niente path traversal; `date` ISO reale; `minutes` int > 0;
  `description` non vuota), **appende in modo atomico** (tmp + `os.replace`, no shell) la voce a questo file,
  poi **rigenera l'SQLite serving** in-process così la voce compare subito in `GET /api/v2/stats/hours`.
  La voce inserita ha sempre `source: "manual"` e `ledger_mission: "M-LEDGER-<PROJECT>"`.

Le voci aggiunte via endpoint rispettano lo **stesso schema** descritto sopra: i due modi scrivono lo
stesso file con lo stesso contratto.

## Serving
`GET /api/v2/stats/hours` → lista per progetto `{project, minutes, hours, manual_minutes,
commit_minutes}` ordinata per minuti. Meta SQLite: `time_entries_manual`,
`time_entries_commit`.

## Primo dato reale
Capasso: 300 min (`incontro Stefania`, `M-LEDGER-CAPASSO`) + stima-commit.
