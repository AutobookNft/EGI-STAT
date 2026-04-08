"""
Mission Registry → DB pipeline.

Reads stats from MISSION_REGISTRY.json (the source of truth) and writes
them into the same DB tables that EGI-STAT frontend already reads:
daily_stats, weekly_stats, mission_stats.

Existing data from commits stays. Where a mission overlaps with an
existing day+repo row, the mission data overwrites it (more precise).

@author Padmin D. Curtis (AI Partner OS3.0) for Fabio Cherici
@version 3.0.0 (FlorenceEGI — EGI-STAT)
@date 2026-04-08
@purpose Registry JSON → DB. That's it.
"""

import json
import os
import sys
import argparse
import math
from datetime import datetime, date, timedelta
from collections import defaultdict
import psycopg2
from psycopg2.extras import Json
import dotenv
from pathlib import Path

dotenv.load_dotenv(Path(__file__).parent / ".env")

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_DATABASE")
DB_USER = os.getenv("DB_USERNAME")
DB_PASS = os.getenv("DB_PASSWORD")
DB_SCHEMA = os.getenv("DB_SCHEMA", "stat")

REGISTRY_PATH = os.getenv(
    "MISSION_REGISTRY_PATH",
    "/home/fabio/EGI-DOC/docs/missions/MISSION_REGISTRY.json"
)

# Organ name → repo_name as it appears in stat.daily_stats / stat.commits
ORGAN_TO_REPO = {
    "EGI": "florenceegi/EGI",
    "EGI-HUB": "florenceegi/EGI-HUB",
    "EGI-HUB-HOME": "florenceegi/EGI-HUB-HOME-REACT",
    "EGI-SIGILLO": "florenceegi/EGI-SIGILLO",
    "EGI-Credential": "florenceegi/egi-credential",
    "NATAN_LOC": "florenceegi/NATAN_LOC",
    "EGI-INFO": "florenceegi/EGI-INFO",
    "EGI-DOC": "florenceegi/EGI-DOC",
    "EGI-STAT": "florenceegi/EGI-STAT",
}


def get_connection():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASS
    )


def load_missions():
    """Load completed missions with stats from MISSION_REGISTRY.json."""
    with open(REGISTRY_PATH) as f:
        registry = json.load(f)

    missions = []
    for m in registry.get("missions", []):
        if m.get("stato") != "completed":
            continue
        if not m.get("stats"):
            continue
        if not m.get("data_apertura") or not m.get("data_chiusura") or m["data_chiusura"] == "pending":
            continue
        missions.append(m)

    return missions


def write_mission_stats(missions, conn):
    """Write each mission's stats into stat.mission_stats."""
    cur = conn.cursor()

    for m in missions:
        s = m["stats"]
        organs = m.get("organi_coinvolti", [])
        repos = [ORGAN_TO_REPO[o] for o in organs if o in ORGAN_TO_REPO]

        cur.execute(f"""
            INSERT INTO {DB_SCHEMA}.mission_stats
                (mission_id, title, date_opened, date_closed, status,
                 mission_type, organs, repos, cross_organ,
                 files_modified, files_count, files_created,
                 doc_sync_executed, doc_verified, duration_days, type_weight,
                 total_commits, weighted_commits, lines_added, lines_deleted,
                 lines_net, lines_touched, cognitive_load, productivity_index,
                 day_type, tags_breakdown)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (mission_id) DO UPDATE SET
                title=EXCLUDED.title, date_closed=EXCLUDED.date_closed,
                status=EXCLUDED.status, mission_type=EXCLUDED.mission_type,
                organs=EXCLUDED.organs, repos=EXCLUDED.repos,
                cross_organ=EXCLUDED.cross_organ, files_modified=EXCLUDED.files_modified,
                files_count=EXCLUDED.files_count, doc_sync_executed=EXCLUDED.doc_sync_executed,
                total_commits=EXCLUDED.total_commits, weighted_commits=EXCLUDED.weighted_commits,
                lines_added=EXCLUDED.lines_added, lines_deleted=EXCLUDED.lines_deleted,
                lines_net=EXCLUDED.lines_net, lines_touched=EXCLUDED.lines_touched,
                cognitive_load=EXCLUDED.cognitive_load, productivity_index=EXCLUDED.productivity_index,
                day_type=EXCLUDED.day_type, tags_breakdown=EXCLUDED.tags_breakdown,
                ingested_at=CURRENT_TIMESTAMP
        """, (
            m["mission_id"], m.get("titolo", ""), m["data_apertura"], m["data_chiusura"],
            m.get("stato"), m.get("tipo_missione"), Json(organs), Json(repos),
            m.get("cross_organo", False), Json(m.get("files_modified", [])),
            s.get("files_touched", 0), m.get("files_created", 0),
            m.get("doc_sync_executed", False), m.get("doc_verified", False),
            max(1, (datetime.strptime(m["data_chiusura"][:10], "%Y-%m-%d") -
                     datetime.strptime(m["data_apertura"][:10], "%Y-%m-%d")).days + 1),
            1.0,
            s["total_commits"], s["weighted_commits"], s["lines_added"], s["lines_deleted"],
            s["lines_net"], s["lines_touched"], s["cognitive_load"], s["productivity_index"],
            s.get("day_type", "MIXED"), Json(s.get("tags_breakdown", {}))
        ))

        print(f"  {m['mission_id']} | {s['total_commits']:3d} commits | "
              f"+{s['lines_added']:5d} -{s['lines_deleted']:5d} = {s['lines_net']:+6d} net | "
              f"{s['files_touched']:3d} files | PI:{s['productivity_index']:7.2f}")

    conn.commit()
    print(f"\n  ✓ {len(missions)} missions → mission_stats")


def enrich_daily_stats(missions, conn):
    """Overwrite daily_stats where a mission overlaps with existing rows."""
    cur = conn.cursor()
    updated = 0

    for m in missions:
        s = m["stats"]
        if s["total_commits"] == 0:
            continue

        date_opened = datetime.strptime(m["data_apertura"][:10], "%Y-%m-%d").date()
        date_closed = datetime.strptime(m["data_chiusura"][:10], "%Y-%m-%d").date()
        organs = m.get("organi_coinvolti", [])
        repos = [ORGAN_TO_REPO[o] for o in organs if o in ORGAN_TO_REPO]

        mission_ids = [m["mission_id"]]
        mission_types = [m.get("tipo_missione", "feature")]
        is_cross = m.get("cross_organo", False)

        # For each day in the mission range, update matching daily_stats rows
        d = date_opened
        while d <= date_closed:
            for repo in repos:
                cur.execute(f"""
                    UPDATE {DB_SCHEMA}.daily_stats
                    SET mission_ids = %s,
                        mission_types = %s,
                        mission_count = COALESCE(mission_count, 0) + 1,
                        doc_sync_count = CASE WHEN %s THEN COALESCE(doc_sync_count, 0) + 1 ELSE COALESCE(doc_sync_count, 0) END,
                        cross_organ = %s
                    WHERE date = %s AND repo_name = %s
                      AND (mission_ids IS NULL OR NOT mission_ids @> %s::jsonb)
                """, (
                    Json(mission_ids), Json(mission_types),
                    m.get("doc_sync_executed", False), is_cross,
                    d, repo, Json(mission_ids)
                ))
                updated += cur.rowcount
            d += timedelta(days=1)

    conn.commit()
    print(f"  ✓ {updated} daily_stats rows enriched")


def enrich_weekly_stats(missions, conn):
    """Update weekly_stats with mission counts."""
    cur = conn.cursor()
    week_data = defaultdict(lambda: {"count": 0, "types": set(), "sync": 0})

    for m in missions:
        if m["stats"]["total_commits"] == 0:
            continue
        dc = datetime.strptime(m["data_chiusura"][:10], "%Y-%m-%d").date()
        iso = dc.isocalendar()
        key = (iso[0], iso[1])
        week_data[key]["count"] += 1
        week_data[key]["types"].add(m.get("tipo_missione", "feature"))
        if m.get("doc_sync_executed"):
            week_data[key]["sync"] += 1

    updated = 0
    for (year, week), wd in week_data.items():
        rate = wd["sync"] / wd["count"] if wd["count"] > 0 else 0
        cur.execute(f"""
            UPDATE {DB_SCHEMA}.weekly_stats
            SET mission_count = %s, mission_types = %s, doc_sync_rate = %s
            WHERE year = %s AND week = %s
        """, (wd["count"], Json(list(wd["types"])), rate, year, week))
        updated += cur.rowcount

    conn.commit()
    print(f"  ✓ {updated} weekly_stats rows enriched")


def main():
    print(f"{'='*70}")
    print(f"  Registry → DB Pipeline v3.0 — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  Source: {REGISTRY_PATH}")
    print(f"{'='*70}\n")

    missions = load_missions()
    print(f"  {len(missions)} completed missions with stats\n")

    if not missions:
        print("  Nothing to ingest.")
        return

    conn = get_connection()
    try:
        write_mission_stats(missions, conn)
        enrich_daily_stats(missions, conn)
        enrich_weekly_stats(missions, conn)
    finally:
        conn.close()

    print(f"\n  Done.")


if __name__ == "__main__":
    main()
