# Patch additiva PROPOSTA — STATS_SYSTEM_SSOT.md (cross-organo)

> Target: `/home/fabio/os3-matrix/docs/stats/STATS_SYSTEM_SSOT.md`
> Mission: M-STAT-001 — builder stats.db esporta `trigger_matrix` + `design`
> Mode: ADDITIVE — NON auto-applicata (fuori instance_root EGI-STAT; Regole assolute 6/9).
> Da applicare via DOC-SYNC dell'organo proprietario (os3-matrix), oppure manualmente dal CEO.
> Hash file al momento della proposta: 00df94283e16a98ab529d71b190903478ca300f50aa635796716b4241765fbc3

## Inserimento 1 — estendere lo schema della tabella `missions_open`

Nella sezione **"### Mission IN CORSO — tabella `missions_open` + endpoint"** (intorno a riga 608),
l'elenco colonne attuale:

```
Nuova tabella **`missions_open`** nello SQLite serving (`organ, id` PK; `title, raw_status,
mission_type, date_opened, discovered_at`; indici su `organ` e `raw_status`)
```

diventa:

```
Nuova tabella **`missions_open`** nello SQLite serving (`organ, id` PK; `title, raw_status,
mission_type, date_opened, trigger_matrix, design, discovered_at`; indici su `organ` e `raw_status`)
```

## Inserimento 2 — nuovo blockquote di delta (dopo §Mission IN CORSO, prima di §Copertura repo)

```
### Campi-scheda dettaglio: `trigger_matrix` + `design` (M-STAT-001, 2026-06-25, ADDITIVO)

> **Cosa.** Il builder stats.db esporta due colonne aggiuntive **in entrambe** le tabelle `missions`
> (asse produzione) e `missions_open` (WIP): **`trigger_matrix`** (INTEGER, `1..6` dalla Trigger Matrix
> DOC-SYNC, o `NULL`) e **`design`** (TEXT, `'ok'|'waiver'|NULL`, governance del design gate). Servono al
> cockpit Nexus per la **scheda dettaglio** della mission.
>
> **Come.** `ecosystem.normalize_mission`/`normalize_open_mission` derivano i campi dal registry:
> `trigger_matrix` passa-attraverso da `m['trigger_matrix']`; `design` mappa `design_fingerprint → 'ok'`,
> `design_waiver → 'waiver'`, altrimenti `None`. `aggregate_to_sqlite.py` (`insert_mission`/`insert_open_mission`)
> scrive le colonne col medesimo upsert `ON CONFLICT(organ,id) DO UPDATE`. Le colonne sono nullable e in
> `DROP_TABLES` (full-rebuild le ricostruisce).
>
> **Confine (Pilastro 3).** Additivo: nessuna metrica di produzione tocca questi campi; conteggi,
> `weighted_commits`, time-series e `_CLOSED_WHERE` **invariati**. Trigger Matrix **tipo 2** (nuove colonne
> additive in tabelle esistenti, contratti di conteggio invariati). **Speculare al serving M-NEXUS-008**:
> il cockpit serve i 3 campi-scheda (`trigger_matrix`, `design` + titolo) dal **medesimo SQLite** della
> lista, non più da `bin/mission show` (che sul box leggeva file-registry stali coi path del laptop).
> Test builder: `EGI-STAT/backend/tests/m_fuc_062_builder_test.py` **4/4**. Codice:
> `ecosystem.py::{normalize_mission,normalize_open_mission}`, `aggregate_to_sqlite.py::{insert_mission,insert_open_mission}`.
> Dettaglio EGI-STAT: `EGI-STAT/backend/MULTI_REGISTRY.md` §Campi-scheda dettaglio.
```
