"""
@purpose Test red M-244: il serving settimanale deve esporre il THROUGHPUT v3
         (somma del valore prodotto), e la settimana con piu missioni chiuse
         deve avere il throughput piu alto. Cattura la regressione del grafico
         che mostrava la media (throughput-blind) -> W23 a 25 sotto W19.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import stats_v2


def test_weekly_exposes_throughput_and_intensity():
    rows = stats_v2.aggregate_weekly()
    assert rows, "nessuna riga settimanale"
    for r in rows:
        assert "productivity_throughput" in r
        assert "productivity_intensity" in r


def test_busiest_week_has_max_throughput():
    rows = stats_v2.aggregate_weekly()
    busiest = max(rows, key=lambda r: r["missions_closed"])
    top_thru = max(rows, key=lambda r: r["productivity_throughput"])
    assert busiest["period"] == top_thru["period"], (
        f"busiest={busiest['period']} ma top throughput={top_thru['period']}")
