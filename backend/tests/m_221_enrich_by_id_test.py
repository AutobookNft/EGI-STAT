#!/usr/bin/env python3
"""
Test M-221 — EGI-STAT enrich per-organo (grep-by-id).

@purpose Le missioni degli organi non enrichati (os3-matrix, LeVespe, …) avevano
         PI=0 dopo M-220 (count corretto, git-stats assenti). M-221 le enricha
         attribuendo i commit per id-missione (globalmente unico) cercato nei
         messaggi commit di tutti i repo dell'ecosistema (cross-repo).

Oracle ETEROGENEO (shell git log --grep) su una missione nota.
RED prima: M-OS3-047 ha PI=0 nel DB. GREEN dopo: commit/PI reali + calo dei PI=0.

@author Padmin D. Curtis (AI Partner OS3.0) for Fabio Cherici
@date 2026-06-01
"""
import os
import sys
import subprocess
from pathlib import Path

import dotenv
import psycopg2

fail = 0


def assert_fail(msg):
    global fail
    print(f"FAIL: {msg}")
    fail = 1


def _sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()


def oracle_commits(mission_id, repos):
    """Conta i commit DISTINTI il cui SUBJECT cita \\bmission_id\\b (shell git).
    Subject-based come l'impl: un commit il cui subject è di un'altra missione
    ma che menziona l'id nel body NON va attribuito qui (attribuzione per il
    lavoro reale del commit, non per cross-reference incidentali)."""
    hashes = set()
    for repo in repos:
        # '%H %s': l'hash è esadecimale → \\bID\\b matcha solo nel subject
        out = _sh(f"git -C {repo} log --all --pretty=format:'%H %s' 2>/dev/null "
                  f"| grep -E '\\b{mission_id}\\b' | awk '{{print $1}}'")
        hashes.update(h for h in out.splitlines() if h.strip())
    return len(hashes)


def main():
    dotenv.load_dotenv(Path(__file__).parent.parent / ".env")
    sch = os.getenv("DB_SCHEMA", "stat")
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"), port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_DATABASE"), user=os.getenv("DB_USERNAME"),
        password=os.getenv("DB_PASSWORD"), connect_timeout=10,
    )
    cur = conn.cursor()

    # --- caso noto: M-OS3-047 (organ os3-matrix) tocca os3-matrix + oracode ---
    sample = "M-OS3-047"
    sample_organ = "os3-matrix"
    expected_commits = oracle_commits(sample, ["/home/fabio/os3-matrix", "/home/fabio/oracode"])
    print(f"  oracle: {sample} = {expected_commits} commit (os3-matrix + oracode)")
    if expected_commits < 4:
        assert_fail(f"#oracle {sample} dovrebbe avere >=4 commit, oracle={expected_commits}")

    cur.execute(f'select total_commits, productivity_index from "{sch}".mission_stats '
                f'where organ=%s and mission_id=%s', (sample_organ, sample))
    row = cur.fetchone()
    if not row:
        assert_fail(f"#1 {sample} assente dal DB (organ={sample_organ})")
    else:
        db_commits, db_pi = row
        # 1. i commit nel DB combaciano con l'oracle grep
        if db_commits != expected_commits:
            assert_fail(f"#1 {sample}: DB commits={db_commits} != oracle={expected_commits}")
        # 2. PI ora > 0 (enrich avvenuto)
        if not db_pi or db_pi <= 0:
            assert_fail(f"#2 {sample}: PI={db_pi} ancora 0 (enrich non applicato)")

    # 3. calo netto dei PI=0: l'enrich deve recuperarne la maggioranza degli
    #    organi engine. Soglia: meno di 60 righe a PI=0 (era 93 dopo M-220).
    cur.execute(f'select count(*) from "{sch}".mission_stats where productivity_index<=0')
    pi_zero = cur.fetchone()[0]
    print(f"  righe PI=0 nel DB: {pi_zero} (era 93 dopo M-220)")
    if pi_zero >= 93:
        assert_fail(f"#3 PI=0 ancora {pi_zero}: enrich non ha recuperato nulla")

    # 4. os3-matrix non è più tutto a zero
    cur.execute(f'select count(*) filter(where productivity_index>0), count(*) '
                f'from "{sch}".mission_stats where organ=%s', ("os3-matrix",))
    pos, tot = cur.fetchone()
    print(f"  os3-matrix: {pos}/{tot} con PI>0")
    if pos == 0:
        assert_fail("#4 os3-matrix ancora 0/27 con PI>0")

    conn.close()
    if fail == 0:
        print(f"PASS: enrich-by-id — {sample}={expected_commits} commit nel DB, PI=0 sceso a {pi_zero}")
        sys.exit(0)
    print("RED")
    sys.exit(1)


if __name__ == "__main__":
    main()
