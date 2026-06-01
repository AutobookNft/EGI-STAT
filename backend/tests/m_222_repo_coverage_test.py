#!/usr/bin/env python3
"""
Test M-222 — EGI-STAT: tutti i repo del CEO nei grafici giornalieri.

@purpose I grafici daily/weekly (ingest_to_remotedb → daily_stats) tracciavano
         solo 15 repo florenceegi/*. Mancavano repo con lavoro reale del CEO:
         AutobookNft/pinocapasso (org diversa), florenceegi/le-vespe-cafe,
         florenceegi/os3-matrix. Dopo M-222 i loro commit recenti sono in
         daily_stats → appaiono nei grafici.

RED prima: i 3 repo assenti da daily_stats. GREEN dopo: presenti con commit
del 2026-06-01 (lavoro del CEO di quel giorno).

@author Padmin D. Curtis (AI Partner OS3.0) for Fabio Cherici
@date 2026-06-01
"""
import os
import sys
from pathlib import Path

import dotenv
import psycopg2

# Repo prima non tracciati, con lavoro reale del CEO il 2026-06-01.
EXPECTED_REPOS = [
    "AutobookNft/pinocapasso",
    "florenceegi/le-vespe-cafe",
    "florenceegi/os3-matrix",
]
WORK_DAY = "2026-06-01"
fail = 0


def assert_fail(msg):
    global fail
    print(f"FAIL: {msg}")
    fail = 1


def main():
    dotenv.load_dotenv(Path(__file__).parent.parent / ".env")
    sch = os.getenv("DB_SCHEMA", "stat")
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"), port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_DATABASE"), user=os.getenv("DB_USERNAME"),
        password=os.getenv("DB_PASSWORD"), connect_timeout=10,
    )
    cur = conn.cursor()

    for repo in EXPECTED_REPOS:
        # 1. il repo è in daily_stats
        cur.execute(f'select count(*), max(date) from "{sch}".daily_stats where repo_name=%s', (repo,))
        n, last = cur.fetchone()
        if n == 0:
            assert_fail(f"#1 {repo}: assente da daily_stats (non tracciato nei grafici)")
            continue
        # 2. ha il lavoro del CEO del giorno WORK_DAY
        cur.execute(f'select coalesce(sum(total_commits),0) from "{sch}".daily_stats '
                    f'where repo_name=%s and date=%s', (repo, WORK_DAY))
        commits = cur.fetchone()[0]
        print(f"  {repo:32s} righe daily={n}, ultima={last}, commit {WORK_DAY}={commits}")
        if commits <= 0:
            assert_fail(f"#2 {repo}: nessun commit il {WORK_DAY} in daily_stats (lavoro del CEO non tracciato)")

    conn.close()
    if fail == 0:
        print(f"PASS: i {len(EXPECTED_REPOS)} repo del CEO sono nei grafici con il lavoro del {WORK_DAY}")
        sys.exit(0)
    print("RED")
    sys.exit(1)


if __name__ == "__main__":
    main()
