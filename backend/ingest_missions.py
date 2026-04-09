"""
Mission Registry → DB pipeline v4.0

Reads stats from MISSION_REGISTRY.json and writes them into the SAME
tables the frontend already reads: daily_stats and weekly_stats.
No separate tables. No parallel system.

For each mission: upsert into daily_stats (date + repo) and
recalculate weekly_stats for affected weeks.

@author Padmin D. Curtis (AI Partner OS3.0) for Fabio Cherici
@version 4.0.0 (FlorenceEGI — EGI-STAT)
@date 2026-04-09
@purpose Write mission stats into daily_stats and weekly_stats. Period.
"""

import json
import os
import math
from datetime import datetime, date, timedelta
from collections import defaultdict
import psycopg2
from psycopg2.extras import Json, RealDictCursor
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

# Organ → repo_name as stored in daily_stats/weekly_stats
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

MISSION_TYPE_TO_DAY_TYPE = {
    "feature": ("FEATURE_DEV", "✨", 1.0),
    "bugfix": ("BUG_FIXING", "🐞", 1.3),
    "refactor": ("REFACTORING", "🛠️", 1.5),
    "docsync": ("DOCS", "📝", 0.8),
    "audit": ("MIXED", "📦", 1.1),
    "lso-evolution": ("REFACTORING", "🛠️", 1.5),
}


def get_connection():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASS
    )


def load_missions():
    with open(REGISTRY_PATH) as f:
        registry = json.load(f)
    missions = []
    for m in registry.get("missions", []):
        if m.get("stato") != "completed":
            continue
        if not m.get("stats"):
            continue
        if not m.get("data_chiusura") or m["data_chiusura"] == "pending":
            continue
        missions.append(m)
    return missions


def write_to_daily_stats(missions, conn):
    """Write mission stats into daily_stats — the table the frontend reads."""
    cur = conn.cursor()
    upserted = 0

    for m in missions:
        s = m["stats"]
        if s["total_commits"] == 0 and s["lines_added"] == 0:
            continue

        organs = m.get("organi_coinvolti", [])
        repos = [ORGAN_TO_REPO[o] for o in organs if o in ORGAN_TO_REPO]
        if not repos:
            repos = ["florenceegi/EGI-DOC"]  # fallback for ecosystem/doc missions

        date_closed = m["data_chiusura"][:10]
        mission_type = m.get("tipo_missione", "feature")
        day_type, day_icon, _ = MISSION_TYPE_TO_DAY_TYPE.get(mission_type, ("MIXED", "📦", 1.0))

        # Distribute stats across repos proportionally
        # If mission touches 1 repo, all stats go there
        # If multiple repos, split evenly (approximation)
        n_repos = len(repos)
        for repo in repos:
            commits = s["total_commits"] // n_repos
            lines_added = s["lines_added"] // n_repos
            lines_deleted = s["lines_deleted"] // n_repos
            lines_net = lines_added - lines_deleted
            files = s["files_touched"] // n_repos or 1

            # Weighted commits and PI from stats
            weighted = s["weighted_commits"] / n_repos
            pi = s["productivity_index"] / n_repos
            cl = s["cognitive_load"]
            coding_h = max(0.5, commits * 22 / 60)

            cur.execute(f"""
                INSERT INTO {DB_SCHEMA}.daily_stats
                    (date, repo_name, total_commits, weighted_commits,
                     lines_added, lines_deleted, net_lines,
                     productivity_score, files_touched,
                     day_type, day_type_icon, cognitive_load,
                     coding_hours, testing_hours, tags_breakdown)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (date, repo_name) DO UPDATE SET
                    total_commits = GREATEST({DB_SCHEMA}.daily_stats.total_commits, EXCLUDED.total_commits),
                    weighted_commits = GREATEST({DB_SCHEMA}.daily_stats.weighted_commits, EXCLUDED.weighted_commits),
                    lines_added = GREATEST({DB_SCHEMA}.daily_stats.lines_added, EXCLUDED.lines_added),
                    lines_deleted = GREATEST({DB_SCHEMA}.daily_stats.lines_deleted, EXCLUDED.lines_deleted),
                    net_lines = CASE
                        WHEN EXCLUDED.total_commits > {DB_SCHEMA}.daily_stats.total_commits
                        THEN EXCLUDED.net_lines
                        ELSE {DB_SCHEMA}.daily_stats.net_lines END,
                    productivity_score = GREATEST({DB_SCHEMA}.daily_stats.productivity_score, EXCLUDED.productivity_score),
                    files_touched = GREATEST({DB_SCHEMA}.daily_stats.files_touched, EXCLUDED.files_touched),
                    day_type = CASE
                        WHEN EXCLUDED.total_commits > {DB_SCHEMA}.daily_stats.total_commits
                        THEN EXCLUDED.day_type
                        ELSE {DB_SCHEMA}.daily_stats.day_type END,
                    day_type_icon = CASE
                        WHEN EXCLUDED.total_commits > {DB_SCHEMA}.daily_stats.total_commits
                        THEN EXCLUDED.day_type_icon
                        ELSE {DB_SCHEMA}.daily_stats.day_type_icon END,
                    cognitive_load = GREATEST({DB_SCHEMA}.daily_stats.cognitive_load, EXCLUDED.cognitive_load),
                    coding_hours = GREATEST({DB_SCHEMA}.daily_stats.coding_hours, EXCLUDED.coding_hours)
            """, (
                date_closed, repo, commits, weighted,
                lines_added, lines_deleted, lines_net,
                pi, files, day_type, day_icon, cl,
                coding_h, coding_h, Json(s.get("tags_breakdown", {}))
            ))
            upserted += 1

    conn.commit()
    print(f"  ✓ {upserted} daily_stats rows upserted")
    return upserted


def update_weekly_stats_for_missions(missions, conn):
    """Update weekly_stats ONLY for weeks that have mission data.
    Does NOT rebuild all weeks — preserves existing fixed data."""
    cur = conn.cursor()

    # Find which (year, week) combinations are affected by missions
    affected_weeks = set()
    for m in missions:
        s = m["stats"]
        if s["total_commits"] == 0 and s["lines_added"] == 0:
            continue
        dc = datetime.strptime(m["data_chiusura"][:10], "%Y-%m-%d").date()
        iso = dc.isocalendar()
        affected_weeks.add((iso[0], iso[1]))

    if not affected_weeks:
        print("  ✓ No weekly_stats to update")
        return

    updated = 0
    for (year, week) in affected_weeks:
        cur.execute(f"""
            INSERT INTO {DB_SCHEMA}.weekly_stats (year, week, repo_name, productivity_score, metrics)
            SELECT
                EXTRACT(ISOYEAR FROM date)::int as year,
                EXTRACT(WEEK FROM date)::int as week,
                repo_name,
                SUM(productivity_score) as productivity_score,
                jsonb_build_object(
                    'weighted_commits', SUM(weighted_commits),
                    'lines_touched', SUM(lines_added + lines_deleted),
                    'total_commits', SUM(total_commits)
                ) as metrics
            FROM {DB_SCHEMA}.daily_stats
            WHERE EXTRACT(ISOYEAR FROM date) = %s AND EXTRACT(WEEK FROM date) = %s
            GROUP BY year, week, repo_name
            ON CONFLICT (year, week, repo_name) DO UPDATE SET
                productivity_score = EXCLUDED.productivity_score,
                metrics = EXCLUDED.metrics
        """, (year, week))
        updated += cur.rowcount

    conn.commit()
    print(f"  ✓ {updated} weekly_stats rows updated (only mission weeks)")


def main():
    print(f"{'='*70}")
    print(f"  Mission → daily_stats/weekly_stats v4.0")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  Source: {REGISTRY_PATH}")
    print(f"{'='*70}\n")

    missions = load_missions()
    print(f"  {len(missions)} completed missions with stats\n")

    if not missions:
        print("  Nothing to ingest.")
        return

    conn = get_connection()
    try:
        write_to_daily_stats(missions, conn)
        update_weekly_stats_for_missions(missions, conn)
    finally:
        conn.close()

    print(f"\n  Done.")


if __name__ == "__main__":
    main()
