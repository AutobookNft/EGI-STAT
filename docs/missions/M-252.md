# M-252 — Stat coerenti (card==grafico, mission-only) + meccanismo anti-recidiva

> Report tecnico (FASE 6a). Esteso: M-252_FULL.md.

- **Organo**: EGI-STAT. Trigger=2. Decisione CEO: le statistiche si contano SOLO dentro le mission.
- **Incoerenza risolta**: la card giornaliera (daily_detail, mission-only) e il grafico settimanale (aggregate_daily) mostravano numeri diversi per lo stesso giorno (8 giu: card 37.739 vs grafico 63.688) perché il weekly univa `legacy_repo_day` (mission+legacy). Fix: `aggregate_daily` ora usa la STESSA sorgente `mission_repo_day` (mission-only) → card e grafico coincidono (8 giu: 37.739=37.739). `legacy_repo_day` resta nel DB per l'asse storico/Ore-per-Progetto, ma fuori dalla time-series mission.
- **Anti-recidiva 1 (regex parziale)**: `ecosystem.MISSION_ID_RE` = pattern mission-ID **canonico unico** (`M-(?:[A-Za-z0-9]+-)*\d+`) + `cites_mission()`. Test anti-drift `m_252_canonical_id_test.py`: enumera TUTTI gli id reali nei registry e si **rompe** se un prefisso nuovo non è coperto. Niente più regex fatte a mano che mancano prefissi (il caso `M-FUC-` non riconosciuto non può ripetersi).
- **Anti-recidiva 2 (mis-attribuzione)**: `coherence_check.py` ora segnala le mission CHIUSE con 0 commit attribuiti (i cui commit cadono in "legacy" invece che mission). È il buco — `commit_hashes` vuoti → falso "fuori mission" — che audit e DeepDebug non avevano colto: ora **rilevato automaticamente a ogni check**.
- **Test**: `m_252_card_weekly_coherent_test.py` (card==weekly per giorno) + `m_252_canonical_id_test.py` (anti-drift) → verdi; regressione 24/24.
- **Audit** + **DOC-SYNC**: vedi registry.
