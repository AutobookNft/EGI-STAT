"""
@purpose Test red M-247: il serving stats deve AUTO-RIGENERARSI quando un registry
         e' piu' recente del DB (anti-staleness). Root-cause CEO: la dashboard
         mostrava conteggi vecchi perche' stats.db si aggiornava solo lanciando a
         mano aggregate_to_sqlite. is_stale()/ensure_fresh() chiudono il buco.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import aggregate_to_sqlite as agg


def test_stale_when_db_missing(tmp_path):
    db = tmp_path / "x.db"
    assert agg.is_stale(str(db)) is True


def test_ensure_fresh_builds_when_missing(tmp_path):
    db = tmp_path / "x.db"
    agg.ensure_fresh(str(db))
    assert db.exists(), "ensure_fresh non ha costruito il DB"
    assert agg.is_stale(str(db)) is False, "DB ancora stale dopo ensure_fresh"


def test_stale_after_registry_touched(tmp_path):
    """Se un registry viene modificato dopo il build, il DB risulta stale."""
    db = tmp_path / "x.db"
    agg.ensure_fresh(str(db))
    assert agg.is_stale(str(db)) is False
    # tocca il file piu' recente tra le sorgenti -> deve tornare stale
    srcs = agg.source_files()
    assert srcs, "nessuna sorgente registry trovata"
    newest = max(srcs, key=lambda p: os.path.getmtime(p))
    os.utime(newest, None)  # bump mtime a 'ora'
    assert agg.is_stale(str(db)) is True
