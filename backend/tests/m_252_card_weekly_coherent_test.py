"""
@purpose Test M-252: la card giornaliera (daily_detail, mission-only) e il grafico
         settimanale (aggregate_daily) devono contare LO STESSO per lo stesso giorno.
         Prima il weekly includeva legacy_repo_day (mission+legacy) -> incoerenza
         (8 giu: card 37739 vs grafico 63688). CEO: stat SOLO dentro le mission.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import stats_v2


def test_daily_card_matches_weekly_source_per_day():
    daily = {d["date"]: d["lines_net"] for d in stats_v2.aggregate_daily()}
    # confronta su qualche giorno recente con lavoro
    for day in ("2026-06-07", "2026-06-08"):
        if day not in daily:
            continue
        card = stats_v2.daily_detail(day)["summary"]["net_lines"]
        assert daily[day] == card, f"{day}: weekly-source {daily[day]} != card {card} (mission-only non allineato)"
