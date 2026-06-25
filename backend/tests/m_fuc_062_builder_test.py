"""
@package  EGI-STAT/backend/tests
@author   Padmin D. Curtis (CTO OS3) for Fabio Cherici (CEO)
@version  1.0.0 (M-STAT-001 / M-FUC-062 builder side)
@date     2026-06-25
@purpose  Il builder dello stats.db deve esportare i campi-scheda della mission
          (trigger_matrix, design) letti dal registry, e lo schema SQLite deve
          avere le colonne — così il cockpit serve il dettaglio dal DB (M-FUC-062).
          Senza questo, il dettaglio mostrerebbe '—' per i 3 campi minori.
"""
import sqlite3

import aggregate_to_sqlite as agg
import ecosystem


def test_normalize_mission_exposes_trigger_and_design():
    raw = {"id": "M-X-1", "status": "closed", "title": "t", "date_close": "2026-06-19",
           "trigger_matrix": 3, "design_fingerprint": {"agent": "engineer-x"}}
    nm = ecosystem.normalize_mission(raw)
    assert nm["trigger_matrix"] == 3
    assert nm["design"] == "ok"


def test_normalize_mission_design_waiver_and_none():
    base = {"id": "M-X-2", "status": "closed", "date_close": "2026-06-19"}
    assert ecosystem.normalize_mission({**base, "design_waiver": {"r": "x"}})["design"] == "waiver"
    assert ecosystem.normalize_mission(base)["design"] is None


def test_normalize_open_mission_exposes_trigger_and_design():
    raw = {"id": "M-X-3", "status": "executing", "trigger_matrix": 2,
           "design_fingerprint": {"agent": "engineer-y"}}
    nm = ecosystem.normalize_open_mission(raw)
    assert nm is not None
    assert nm["trigger_matrix"] == 2
    assert nm["design"] == "ok"


def test_schema_has_new_columns():
    conn = sqlite3.connect(":memory:")
    agg.create_schema(conn)
    mcols = {r[1] for r in conn.execute("PRAGMA table_info(missions)")}
    ocols = {r[1] for r in conn.execute("PRAGMA table_info(missions_open)")}
    assert {"trigger_matrix", "design"} <= mcols
    assert {"trigger_matrix", "design"} <= ocols
    conn.close()
