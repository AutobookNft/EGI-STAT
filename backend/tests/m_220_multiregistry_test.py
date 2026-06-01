#!/usr/bin/env python3
"""
Test M-220 — EGI-STAT multi-registry.

@purpose Invariante: dopo l'ingest, mission_stats nel DB rispecchia TUTTI i
         registry dell'ecosistema (non solo EGI-DOC), ogni riga taggata con
         l'organo di provenienza, e il conteggio per-organo combacia col
         registry sorgente. Normalizza i due schemi (legacy-IT + engine-EN).

Oracle ETEROGENEO: calcola l'atteso via shell (find + jq), una via diversa
dall'impl (ecosystem.py usa os.walk + json python) — così un bug nella logica
di discovery NON si replica identico nell'oracle (P2 audit M-220).

RED prima dell'impl: manca la colonna `organ` e il DB ha solo EGI-DOC (150).
GREEN dopo: organ presente, PK (organ, mission_id), count per-organo combacia.

@author Padmin D. Curtis (AI Partner OS3.0) for Fabio Cherici
@date 2026-06-01
"""
import os
import sys
import json
import subprocess
from pathlib import Path

import dotenv
import psycopg2

HOME = "/home/fabio"
# Root da spazzare. Poli vive in /tmp/oracode (fuori HOME). Tutti i repo contano.
SCAN_ROOTS = ["/home/fabio", "/tmp/oracode"]
PROJECTS_JSON = "/home/fabio/oracode-engine/projects.json"
# Organi che DEVONO comparire (sanity anti-regressione discovery, indipendente).
KNOWN_ORGANS = {
    "EGI-DOC", "os3-matrix", "oracode", "Poli-Doc", "Capasso",
    "LeVespe-DOC", "FABIOCHERICI-DOC", "ORACODE-DOC",
}
fail = 0


def assert_fail(msg):
    global fail
    print(f"FAIL: {msg}")
    fail = 1


# ---- ORACLE eterogeneo: via diversa dall'impl (shell find+jq, non os.walk) ----
# L'impl (ecosystem.py) usa os.walk+json python. L'oracle usa find+jq da shell:
# meccanismo indipendente, così un bug nella logica di discovery dell'impl NON
# si replica identico nell'oracle (P2 audit M-220).

# jq: conta missioni "completed" (entrambi gli schemi) con id non-null.
_JQ_COUNT = ('[.missions[] | select(.stato=="completed" or .status=="closed") '
             '| select((.mission_id // .id) != null)] | length')


def _sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()


def _registry_paths():
    """find sui SCAN_ROOTS (pruning node_modules/.git via -prune) UNION i
    registry_path dei descrittori in projects.json (cattura Poli off-root)."""
    paths = set()
    for base in SCAN_ROOTS:
        if not os.path.isdir(base):
            continue
        out = _sh(
            f"find {base} \\( -name node_modules -o -name .git \\) -prune -o "
            f"-name MISSION_REGISTRY.json -print 2>/dev/null")
        for p in out.splitlines():
            if p.strip():
                paths.add(os.path.realpath(p.strip()))
    # descrittori engine (projects.json) — usa jq, non json python
    descs = _sh(f"jq -r '.projects[].descriptor // empty' {PROJECTS_JSON} 2>/dev/null")
    for d in descs.splitlines():
        if d.strip() and os.path.isfile(d.strip()):
            rp = _sh(f"jq -r '.registry_path // empty' {d.strip()} 2>/dev/null")
            if rp and os.path.isfile(rp):
                paths.add(os.path.realpath(rp))
    return sorted(paths)


def expected_completed_by_organ():
    """Oracle: per ogni registry, organ=basename(project root) via shell,
    count completed via jq. Esclude registry vuoti."""
    exp = {}
    for rp in _registry_paths():
        total = _sh(f"jq -r '(.missions // []) | length' {rp} 2>/dev/null") or "0"
        if total == "0":
            continue
        organ = _sh(f"basename $(dirname $(dirname $(dirname {rp})))")
        n = _sh(f"jq -r '{_JQ_COUNT}' {rp} 2>/dev/null")
        exp[organ] = exp.get(organ, 0) + int(n or 0)
    return exp


def main():
    dotenv.load_dotenv(Path(__file__).parent.parent / ".env")
    sch = os.getenv("DB_SCHEMA", "stat")
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"), port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_DATABASE"), user=os.getenv("DB_USERNAME"),
        password=os.getenv("DB_PASSWORD"), connect_timeout=10,
    )
    cur = conn.cursor()

    expected = expected_completed_by_organ()
    eco_total = sum(expected.values())
    print(f"  oracle: {len(expected)} registry, {eco_total} completed ecosistema")
    for o, n in sorted(expected.items()):
        print(f"    {o:42s} {n}")

    # 0. sanity discovery indipendente: gli organi noti DEVONO esserci
    missing_known = KNOWN_ORGANS - set(expected.keys())
    if missing_known:
        assert_fail(f"#0 discovery non trova organi noti: {sorted(missing_known)}")

    # 1. la colonna `organ` esiste su mission_stats
    cur.execute(
        "select count(*) from information_schema.columns "
        "where table_schema=%s and table_name='mission_stats' and column_name='organ'",
        (sch,),
    )
    has_organ = cur.fetchone()[0] == 1
    if not has_organ:
        assert_fail("#1 mission_stats NON ha la colonna 'organ' (multi-registry non implementato)")

    # 2. PK di mission_stats include 'organ' (no collisione mission_id cross-organo)
    cur.execute(
        """select a.attname
           from pg_index i
           join pg_attribute a on a.attrelid=i.indrelid and a.attnum=any(i.indkey)
           where i.indrelid = (%s||'.mission_stats')::regclass and i.indisprimary""",
        (sch,),
    )
    pk_cols = {r[0] for r in cur.fetchall()}
    if "organ" not in pk_cols:
        assert_fail(f"#2 PK mission_stats non include 'organ' (PK attuale: {pk_cols})")

    # 3. count per-organo nel DB == oracle (solo se la colonna esiste)
    if has_organ:
        cur.execute(f'select organ, count(*) from "{sch}".mission_stats group by organ')
        db_by_organ = {r[0]: r[1] for r in cur.fetchall()}
        for organ, exp_n in expected.items():
            db_n = db_by_organ.get(organ, 0)
            if db_n != exp_n:
                assert_fail(f"#3 organ '{organ}': DB={db_n} != atteso={exp_n}")
        # 4. totale ecosistema
        db_total = sum(db_by_organ.values())
        if db_total != eco_total:
            assert_fail(f"#4 totale DB={db_total} != ecosistema={eco_total}")
    else:
        assert_fail("#3 skip: colonna organ assente — impossibile contare per-organo")

    conn.close()
    if fail == 0:
        print(f"PASS: multi-registry — {eco_total} missioni completed su {len(expected)} organi nel DB")
        sys.exit(0)
    else:
        print("RED")
        sys.exit(1)


if __name__ == "__main__":
    main()
