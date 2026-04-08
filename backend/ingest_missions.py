"""
Mission-based statistics enrichment pipeline.

Reads completed missions from MISSION_REGISTRY.json and enriches
the existing daily_stats and weekly_stats with structured mission data.

RULES:
- Existing stats from commits are NEVER deleted
- Only days/repos that overlap with a closed mission get enriched
- Mission data overwrites commit-derived classification when available
  (mission_type is more accurate than tag-based day_type)

@author Padmin D. Curtis (AI Partner OS3.0) for Fabio Cherici
@version 1.0.0 (FlorenceEGI — EGI-STAT)
@date 2026-04-08
@purpose Enrich EGI-STAT with mission-aware metrics
"""

import os
import sys
import argparse
from datetime import datetime, date, timedelta
from collections import defaultdict
import psycopg2
from psycopg2.extras import Json
import dotenv
from pathlib import Path

sys.path.append(str(Path(__file__).parent / "core"))
from core.mission_client import MissionClient, MissionStats

# Load env
dotenv.load_dotenv(Path(__file__).parent / ".env")

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_DATABASE")
DB_USER = os.getenv("DB_USERNAME")
DB_PASS = os.getenv("DB_PASSWORD")
DB_SCHEMA = os.getenv("DB_SCHEMA", "stat")


def get_connection():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASS
    )


def ingest_mission_stats(missions: list[MissionStats], conn):
    """Insert/update mission_stats table."""
    cur = conn.cursor()
    for m in missions:
        cur.execute(f"""
            INSERT INTO {DB_SCHEMA}.mission_stats
                (mission_id, title, date_opened, date_closed, status,
                 mission_type, organs, repos, cross_organ,
                 files_modified, files_count, files_created,
                 doc_sync_executed, doc_verified, duration_days, type_weight)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (mission_id) DO UPDATE SET
                title = EXCLUDED.title,
                date_closed = EXCLUDED.date_closed,
                status = EXCLUDED.status,
                mission_type = EXCLUDED.mission_type,
                organs = EXCLUDED.organs,
                repos = EXCLUDED.repos,
                cross_organ = EXCLUDED.cross_organ,
                files_modified = EXCLUDED.files_modified,
                files_count = EXCLUDED.files_count,
                files_created = EXCLUDED.files_created,
                doc_sync_executed = EXCLUDED.doc_sync_executed,
                doc_verified = EXCLUDED.doc_verified,
                duration_days = EXCLUDED.duration_days,
                type_weight = EXCLUDED.type_weight,
                ingested_at = CURRENT_TIMESTAMP
        """, (
            m.mission_id, m.title, m.date_opened, m.date_closed, m.status,
            m.mission_type, Json(m.organs), Json(m.repos), m.cross_organ,
            Json(m.files_modified), m.files_count, m.files_created,
            m.doc_sync_executed, m.doc_verified, m.duration_days, m.type_weight
        ))
    conn.commit()
    print(f"  ✓ {len(missions)} missions upserted into mission_stats")


def enrich_daily_stats(missions: list[MissionStats], conn):
    """
    Enrich daily_stats with mission data.
    For each day covered by a mission, update the mission-aware columns.
    """
    cur = conn.cursor()

    # Build a map: date → list of missions active on that date
    date_missions: dict[date, list[MissionStats]] = defaultdict(list)
    for m in missions:
        if not m.date_closed:
            continue
        d = m.date_opened
        while d <= m.date_closed:
            date_missions[d].append(m)
            d += timedelta(days=1)

    updated = 0
    for day, day_missions in date_missions.items():
        mission_ids = [m.mission_id for m in day_missions]
        mission_types = list(set(m.mission_type for m in day_missions))
        mission_count = len(day_missions)
        doc_sync_count = sum(1 for m in day_missions if m.doc_sync_executed)
        is_cross = any(m.cross_organ for m in day_missions)

        # Get all repos involved on this day
        day_repos = set()
        for m in day_missions:
            day_repos.update(m.repos)

        # Update daily_stats for each repo that has an existing row for this date
        # We DON'T create new rows — only enrich existing ones
        for repo in day_repos:
            cur.execute(f"""
                UPDATE {DB_SCHEMA}.daily_stats
                SET mission_ids = %s,
                    mission_types = %s,
                    mission_count = %s,
                    doc_sync_count = %s,
                    cross_organ = %s
                WHERE date = %s AND repo_name = %s
            """, (
                Json(mission_ids), Json(mission_types), mission_count,
                doc_sync_count, is_cross, day, repo
            ))
            if cur.rowcount > 0:
                updated += cur.rowcount

        # Also update rows where repo_name matches organ names (some repos use different naming)
        # Handle the "all repos" case for ecosystem-wide missions
        if any(m.cross_organ for m in day_missions):
            cur.execute(f"""
                UPDATE {DB_SCHEMA}.daily_stats
                SET mission_ids = %s,
                    mission_types = %s,
                    mission_count = %s,
                    doc_sync_count = %s,
                    cross_organ = TRUE
                WHERE date = %s
                  AND mission_count = 0
            """, (
                Json(mission_ids), Json(mission_types), mission_count,
                doc_sync_count, day
            ))
            updated += cur.rowcount

    conn.commit()
    print(f"  ✓ {updated} daily_stats rows enriched with mission data")


def enrich_weekly_stats(missions: list[MissionStats], conn):
    """
    Enrich weekly_stats with mission counts and doc_sync rate.
    """
    cur = conn.cursor()

    # Group missions by ISO week
    week_missions: dict[tuple[int, int], list[MissionStats]] = defaultdict(list)
    for m in missions:
        if not m.date_closed:
            continue
        iso = m.date_closed.isocalendar()
        week_missions[(iso[0], iso[1])].append(m)

    updated = 0
    for (year, week), wk_missions in week_missions.items():
        mission_count = len(wk_missions)
        mission_types = list(set(m.mission_type for m in wk_missions))
        doc_sync_done = sum(1 for m in wk_missions if m.doc_sync_executed)
        doc_sync_rate = doc_sync_done / mission_count if mission_count > 0 else 0

        # Update all weekly_stats rows for this year/week
        cur.execute(f"""
            UPDATE {DB_SCHEMA}.weekly_stats
            SET mission_count = %s,
                mission_types = %s,
                doc_sync_rate = %s
            WHERE year = %s AND week = %s
        """, (mission_count, Json(mission_types), doc_sync_rate, year, week))
        updated += cur.rowcount

    conn.commit()
    print(f"  ✓ {updated} weekly_stats rows enriched with mission data")


def main():
    parser = argparse.ArgumentParser(description="Mission-based statistics enrichment")
    parser.add_argument("--days", type=int, default=None,
                        help="Only process missions closed in the last N days")
    parser.add_argument("--all", action="store_true",
                        help="Process all completed missions")
    args = parser.parse_args()

    print(f"{'='*50}")
    print(f"  Mission Stats Enrichment — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*50}")

    client = MissionClient()

    if args.all:
        missions = client.get_completed_missions()
        print(f"  Found {len(missions)} completed missions (all time)")
    elif args.days:
        since = date.today() - timedelta(days=args.days)
        missions = client.get_missions_since(since)
        print(f"  Found {len(missions)} missions closed since {since}")
    else:
        # Default: last 7 days
        since = date.today() - timedelta(days=7)
        missions = client.get_missions_since(since)
        print(f"  Found {len(missions)} missions closed in last 7 days")

    if not missions:
        print("  No missions to process.")
        return

    conn = get_connection()
    try:
        ingest_mission_stats(missions, conn)
        enrich_daily_stats(missions, conn)
        enrich_weekly_stats(missions, conn)
    finally:
        conn.close()

    print(f"\n  Done. {len(missions)} missions processed.")


if __name__ == "__main__":
    main()
