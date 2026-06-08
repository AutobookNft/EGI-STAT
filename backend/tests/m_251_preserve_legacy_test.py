"""
@purpose Test M-251: il rebuild atomico (M-250) deve PRESERVARE le tabelle non
         gestite da aggregate (legacy_production, legacy_repo_day). M-250 creava
         un DB nuovo da zero -> le legacy sparivano -> righe nette per repo a 0.
"""
import os, sys, sqlite3
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import aggregate_to_sqlite as agg


def test_legacy_table_survives_rebuild(tmp_path):
    db = str(tmp_path / "s.db")
    agg.aggregate(db)  # primo build
    # simulo la tabella legacy popolata da un ingest separato
    c = sqlite3.connect(db)
    c.execute("CREATE TABLE legacy_production (organ TEXT, lines_net INT)")
    c.execute("INSERT INTO legacy_production VALUES ('EGI', 696000)")
    c.commit(); c.close()
    # rebuild atomico: la legacy NON deve sparire
    agg.aggregate(db)
    c = sqlite3.connect(db)
    got = c.execute("SELECT lines_net FROM legacy_production WHERE organ='EGI'").fetchone()
    assert got is not None and got[0] == 696000, "legacy_production persa nel rebuild atomico"
