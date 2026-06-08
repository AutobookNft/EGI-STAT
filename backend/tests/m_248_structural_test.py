"""
@purpose Test RED M-248: fix strutturale stats.
  H1 — chiave composita (organ,id): mission DIVERSE con stesso id (collisione
       cross-registry post M-OS3-096) NON devono collassare; copie GENUINE
       (stesso title+date_opened) devono fondersi in 1 riga.
  H2 — mission_organs: una mission cross-organo conta su ogni organo toccato.
  H3 — regola 'delivered': status non-terminale ma date_close valido => conta.
  H6 — invariante: l'aggregatore non inserisce righe che il serving filtra fuori.
"""
import os, sys, sqlite3
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import aggregate_to_sqlite as agg
import ecosystem


def _nm(mid, organ, title, dopen="2026-06-01", dclose="2026-06-02", organs=None, commit_hashes=None):
    return {
        "id": mid, "title": title, "status": "completed",
        "date_opened": dopen, "date_closed": dclose, "mission_type": "feature",
        "organs": organs if organs is not None else [organ], "cross_organ": bool(organs and len(organs) > 1),
        "files_modified": [], "doc_sync_executed": False,
        "stats": {"commit_hashes": commit_hashes or [], "total_commits": len(commit_hashes or [])},
        "has_git_stats": bool(commit_hashes),
    }


def _fresh_db(tmp_path):
    db = str(tmp_path / "t.db")
    conn = sqlite3.connect(db)
    agg.create_schema(conn)
    return conn


# ---- H1: collisione id = mission diverse -> righe distinte (chiave composita) ----
def test_h1_collision_kept_separate(tmp_path):
    conn = _fresh_db(tmp_path)
    agg.insert_mission(conn, "EGI-DOC", "/r/egidoc", _nm("M-242", "EGI-DOC", "Fix label AdminChart"))
    agg.insert_mission(conn, "EGI", "/r/egi", _nm("M-242", "EGI", "Thumbnail modale Creator"))
    conn.commit()
    n = conn.execute("SELECT COUNT(*) FROM missions WHERE id='M-242'").fetchone()[0]
    assert n == 2, f"collisione id collassata: {n} righe invece di 2"


# ---- H1: copia genuina (stesso title+date) -> 1 riga fusa ----
def test_h1_genuine_copy_merged(tmp_path):
    conn = _fresh_db(tmp_path)
    copies = [
        ("oracode", "/r/oracode", _nm("M-OS3-022", "oracode", "Paradigm relocation", commit_hashes=["a"])),
        ("os3-matrix", "/r/os3", _nm("M-OS3-022", "os3-matrix", "Paradigm relocation", commit_hashes=["a", "b"])),
    ]
    agg.merge_and_insert(conn, "M-OS3-022", copies)  # helper Pass2 da implementare
    conn.commit()
    n = conn.execute("SELECT COUNT(*) FROM missions WHERE id='M-OS3-022'").fetchone()[0]
    assert n == 1, f"copia genuina non fusa: {n} righe"


# ---- H2: mission_organs popolata, cross-organo conta su N organi ----
def test_h2_mission_organs(tmp_path):
    conn = _fresh_db(tmp_path)
    agg.insert_mission(conn, "EGI-STAT", "/r/stat",
                       _nm("M-049", "EGI-STAT", "x", organs=["EGI-DOC", "EGI-STAT", "oracode"]))
    conn.commit()
    organs = {r[0] for r in conn.execute(
        "SELECT organ_touched FROM mission_organs WHERE mission_id='M-049'")}
    assert organs == {"EGI-DOC", "EGI-STAT", "oracode"}, f"organi persi: {organs}"


# ---- H3: regola delivered ----
def test_h3_delivered_rule():
    m = {"id": "M-244", "status": "auditing", "title": "x",
         "date_open": "2026-06-07", "date_close": "2026-06-08"}
    nm = ecosystem.normalize_mission(m)
    assert nm is not None, "mission auditing con date_close esclusa (regola delivered mancante)"
    # senza date_close resta esclusa
    m2 = dict(m); m2["date_close"] = None
    assert ecosystem.normalize_mission(m2) is None, "auditing senza date_close non deve contare"


# ---- H6: invariante chiuso (su DB reale auto-build) ----
def test_h6_no_unclosed_rows(tmp_path):
    db = str(tmp_path / "real.db")
    agg.aggregate(db)
    conn = sqlite3.connect(db)
    bad = conn.execute(
        "SELECT COUNT(*) FROM missions WHERE NOT (date_closed IS NOT NULL AND date_closed!='' AND date_closed!='pending')"
    ).fetchone()[0]
    assert bad == 0, f"{bad} righe in missions che il serving filtra fuori (_CLOSED_WHERE)"
