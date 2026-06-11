#!/usr/bin/env python3
"""
Test M-224 — EGI-STAT stats_v2 multi-registry.

@purpose I grafici v2 (line-chart) usavano stats_v2 che leggeva un solo registry
         (EGI-DOC, schema-IT) → scartava le missioni schema-engine e gli altri
         organi → settimane recenti a zero. M-224 ripunta stats_v2 sulla tabella
         mission_stats (218 missioni, 10 organi, PI reali). Le settimane recenti
         tornano non-zero e multi-organo.

Oracle ETEROGENEO: query SQL diretta su mission_stats per settimana di
date_closed, confrontata con l'output di stats_v2.aggregate_weekly().

RED prima: stats_v2 legge il registry → W23 conta poche missioni EGI-DOC.
GREEN dopo: aggregate_weekly == conteggio DB per settimana, recenti non-zero.

@author Padmin D. Curtis (AI Partner OS3.0) for Fabio Cherici
@date 2026-06-01
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # backend/ per importare stats_v2

import dotenv
import psycopg2

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

    # --- ORACLE: missioni chiuse per settimana ISO, da mission_stats (SQL) ---
    cur.execute(
        f"""select extract(isoyear from date_closed)::int,
                   extract(week    from date_closed)::int,
                   count(*)
            from "{sch}".mission_stats
            where date_closed is not null
            group by 1,2""")
    oracle = {f"{y}-W{w:02d}": n for y, w, n in cur.fetchall()}
    oracle_total = sum(oracle.values())
    conn.close()

    # --- stats_v2.aggregate_weekly() (l'impl che alimenta /api/v2/stats/weekly) ---
    import stats_v2
    weekly = stats_v2.aggregate_weekly()
    impl = {w["period"]: w["missions_closed"] for w in weekly}
    impl_total = sum(impl.values())

    print(f"  oracle (DB mission_stats): {len(oracle)} settimane, {oracle_total} missioni")
    print(f"  stats_v2.aggregate_weekly: {len(impl)} settimane, {impl_total} missioni")

    # 1. le settimane recenti NON sono zero (il sintomo del CEO)
    for wk in ("2026-W21", "2026-W22", "2026-W23"):
        if impl.get(wk, 0) <= 0:
            assert_fail(f"#1 {wk}: stats_v2 missions_closed={impl.get(wk,0)} (grafico a zero)")
        else:
            print(f"    {wk}: stats_v2={impl.get(wk)} (oracle {oracle.get(wk)})")

    # 2. multi-organo: il totale combacia col DB (non i ~150 EGI-DOC-only)
    if impl_total != oracle_total:
        assert_fail(f"#2 totale stats_v2={impl_total} != DB mission_stats={oracle_total}")

    # 3. ogni settimana di stats_v2 combacia con l'oracle DB
    for wk, n in oracle.items():
        if impl.get(wk, 0) != n:
            assert_fail(f"#3 {wk}: stats_v2={impl.get(wk,0)} != DB={n}")

    if fail == 0:
        print(f"PASS: stats_v2 multi-registry — {impl_total} missioni, settimane recenti non-zero")
        sys.exit(0)
    print("RED")
    sys.exit(1)


if __name__ == "__main__":
    main()
