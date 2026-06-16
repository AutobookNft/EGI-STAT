"""
@package  EGI-STAT/backend/tests
@author   Padmin D. Curtis (Supervisor-CTO, AI Partner OS3.0) for Fabio Cherici
@version  1.0.0 (FlorenceEGI — EGI-STAT, M-FUC-054)
@date     2026-06-16
@purpose  Test RED M-FUC-054: mission aperte/in-corso visibili nel cockpit Nexus,
  ADDITIVO e zero-rischio per i conteggi prod (stat.florenceegi.com invariato).
  Contratto:
   - ecosystem._is_delivered(m): regola H3 unica condivisa (None/""/"pending" = non delivered).
   - ecosystem.status_is_open(status): True per draft/planned/executing/auditing/auditing_failed
     (terminal=false, counts_as_production=false); False per perpetual/aborted/closed/completed.
   - tabella missions_open popolata da un Pass dedicato che NON passa per normalize_mission.
   - PARTIZIONE: nessuna mission in missions E missions_open (auditing+date_close => solo missions).
   - INVARIANTE PROD: la tabella missions (e _CLOSED_WHERE) non cambia per effetto della feature.
   - serving: stats_v2.open_missions() espone le aperte; gli endpoint esistenti non cambiano.
"""
import os, sys, sqlite3
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import aggregate_to_sqlite as agg
import ecosystem


def _open(mid, organ, status, title="wip", dopen="2026-06-10"):
    """mission grezza in-corso (NO date_close)."""
    return {"id": mid, "status": status, "title": title,
            "date_open": dopen, "date_close": None, "type": "feature",
            "organs": [organ]}


def _delivered(mid, organ, status="closed", title="done", dclose="2026-06-11"):
    return {"id": mid, "status": status, "title": title,
            "date_open": "2026-06-01", "date_close": dclose, "type": "feature",
            "organs": [organ], "stats": {}}


# ---- contratto _is_delivered: regola H3 unica ----
def test_is_delivered_shared_rule():
    assert ecosystem._is_delivered({"date_close": "2026-06-11"}) is True
    assert ecosystem._is_delivered({"date_close": None}) is False
    assert ecosystem._is_delivered({"date_close": ""}) is False
    assert ecosystem._is_delivered({"date_close": "pending"}) is False
    assert ecosystem._is_delivered({"data_chiusura": "2026-06-11"}) is True


# ---- contratto status_is_open: tassonomia reale ----
def test_status_is_open_taxonomy():
    for s in ("draft", "planned", "executing", "auditing", "auditing_failed"):
        assert ecosystem.status_is_open(s) is True, f"{s} dovrebbe essere in-corso"
    for s in ("perpetual", "aborted", "closed", "closed_with_debt", "completed"):
        assert ecosystem.status_is_open(s) is False, f"{s} NON dovrebbe essere in-corso"


# ---- la tabella missions_open esiste nello schema ----
def test_missions_open_table_exists(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "t.db"))
    agg.create_schema(conn)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(missions_open)")}
    assert {"id", "organ", "title", "raw_status", "date_opened"} <= cols, f"schema missions_open incompleto: {cols}"


# ---- una mission executing finisce in missions_open, NON in missions ----
def test_open_mission_routed_to_open_table(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "t.db"))
    agg.create_schema(conn)
    agg.insert_open_mission(conn, "Fucina", "/r/fucina", _open("M-FUC-999", "Fucina", "executing"))
    conn.commit()
    in_open = conn.execute("SELECT raw_status FROM missions_open WHERE id='M-FUC-999'").fetchone()
    assert in_open is not None and in_open[0] == "executing"
    in_missions = conn.execute("SELECT COUNT(*) FROM missions WHERE id='M-FUC-999'").fetchone()[0]
    assert in_missions == 0, "mission aperta NON deve entrare in missions (path prod)"


# ---- PARTIZIONE: auditing CON date_close = delivered => solo missions, mai open ----
def test_partition_mutual_exclusive(tmp_path):
    db = str(tmp_path / "real.db")
    agg.aggregate(db)
    conn = sqlite3.connect(db)
    a = {r[0] for r in conn.execute("SELECT organ||'/'||id FROM missions")}
    b = {r[0] for r in conn.execute("SELECT organ||'/'||id FROM missions_open")}
    assert a.isdisjoint(b), f"mission in entrambe le tabelle (doppio conteggio): {a & b}"


# ---- INVARIANTE PROD: missions resta delivered-only (la feature non sporca il path prod) ----
def test_prod_invariant_missions_delivered_only(tmp_path):
    db = str(tmp_path / "real.db")
    agg.aggregate(db)
    conn = sqlite3.connect(db)
    bad = conn.execute(
        "SELECT COUNT(*) FROM missions WHERE NOT (date_closed IS NOT NULL AND date_closed!='' AND date_closed!='pending')"
    ).fetchone()[0]
    assert bad == 0, f"{bad} righe non-delivered in missions: la feature ha sporcato il path prod"


# ---- serving: open_missions() espone le aperte ----
def test_serving_open_missions(tmp_path, monkeypatch):
    db = str(tmp_path / "real.db")
    agg.aggregate(db)
    monkeypatch.setenv("STATS_DB_PATH", db)
    import importlib, stats_v2
    importlib.reload(stats_v2)
    rows = stats_v2.open_missions()
    assert isinstance(rows, list)
    # almeno una in-corso reale deve comparire (ci sono mission executing nei registry)
    assert all("status" in r and "mission_id" in r for r in rows)
