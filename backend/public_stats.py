"""
@package EGI-STAT — Public Stats
@author Padmin D. Curtis (AI Partner OS3.0) for Fabio Cherici
@version 1.0.0 (FlorenceEGI — EGI-STAT)
@date 2026-06-11
@purpose Aggregato PUBBLICO minimo per il widget "cantiere aperto" di
         fabiocherici.com (M-266). SOLO numeri aggregati — MAI nomi progetto,
         mission, o dettagli (la dashboard resta dietro basic auth).
         Fonti: pattern stats_v2 (M-234 time_entries, M-OS3-086 lines_net
         mission+legacy). Onestà epistemica: hours = manual+stima-commit,
         dichiarato nel campo hours_note.
"""

from datetime import datetime, timezone

from stats_v2 import _connect, _CLOSED_WHERE


def site_stats() -> dict:
    """Aggregato minimo per il sito pubblico.

    Espone SOLO totali: niente nomi progetto/mission (privacy by design —
    il dettaglio vive nella dashboard dietro basic auth).
    """
    conn = _connect()
    try:
        hours_row = conn.execute(
            """
            SELECT COALESCE(SUM(minutes), 0)                                   AS total_minutes,
                   COALESCE(SUM(CASE WHEN date >= date('now', '-7 day')
                                     THEN minutes ELSE 0 END), 0)              AS minutes_7d,
                   COUNT(DISTINCT project)                                     AS projects_total,
                   COUNT(DISTINCT CASE WHEN date >= date('now', '-30 day')
                                       THEN project END)                       AS projects_active_30d,
                   MAX(date)                                                   AS last_entry_date
            FROM time_entries
            """
        ).fetchone()

        # Righe nette totali = produzione mission chiuse + legacy storico (M-OS3-086)
        lines_mission = conn.execute(
            f"SELECT COALESCE(SUM(lines_net), 0) AS ln FROM missions WHERE {_CLOSED_WHERE}"
        ).fetchone()["ln"] or 0
        try:
            lines_legacy = conn.execute(
                "SELECT COALESCE(SUM(lines_net), 0) AS ln FROM legacy_production"
            ).fetchone()["ln"] or 0
        except Exception:
            lines_legacy = 0  # legacy_production assente → solo mission

        # Ultima attività: la più recente tra ledger ore e chiusure mission
        last_mission = conn.execute(
            f"SELECT MAX(date_closed) AS d FROM missions WHERE {_CLOSED_WHERE}"
        ).fetchone()["d"]
    finally:
        conn.close()

    last_activity = max(filter(None, [hours_row["last_entry_date"], last_mission]), default=None)

    return {
        "hours_total": round((hours_row["total_minutes"] or 0) / 60.0, 1),
        "hours_last_7_days": round((hours_row["minutes_7d"] or 0) / 60.0, 1),
        "hours_note": "manual + commit-estimate",
        "projects_total": hours_row["projects_total"] or 0,
        "projects_active_30d": hours_row["projects_active_30d"] or 0,
        "last_activity": last_activity,
        "lines_net_total": lines_mission + lines_legacy,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
