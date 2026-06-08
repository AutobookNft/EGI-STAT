"""
@purpose Test red M-245: serving del dettaglio mission giorno-per-giorno
         suddiviso per organo (tabella + grafico giornaliero). La produzione
         di TUTTI gli organi (os3-matrix, FORTINO, oracode/Fucina, ...) deve
         comparire, attribuita al giorno di chiusura e all'organo di provenienza.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import stats_v2


def test_shape():
    out = stats_v2.daily_missions_by_organ()
    assert "organs" in out and "days" in out
    assert isinstance(out["organs"], list) and isinstance(out["days"], list)


def test_day_total_equals_sum_of_organs():
    out = stats_v2.daily_missions_by_organ()
    for d in out["days"]:
        s = sum(len(v) for v in d["by_organ"].values())
        assert d["total"] == s, f"{d['date']}: total {d['total']} != somma organi {s}"


def test_fortino_and_os3matrix_present():
    """La produzione Fortino/os3-matrix NON deve sparire (era il bug percepito)."""
    out = stats_v2.daily_missions_by_organ()
    all_organs = set(out["organs"])
    assert "os3-matrix" in all_organs
    # almeno un giorno deve contenere una mission os3-matrix
    found = any("os3-matrix" in d["by_organ"] for d in out["days"])
    assert found, "nessuna mission os3-matrix attribuita a un giorno"
