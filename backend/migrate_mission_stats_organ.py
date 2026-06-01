"""
migrate_mission_stats_organ.py — M-220

@purpose Aggiunge la dimensione `organ` a stat.mission_stats e sposta la PK da
         (mission_id) a (organ, mission_id), così che missioni con lo stesso
         mission_id in organi diversi (es. oracode M-001 vs EGI-DOC M-001) non
         collidano. Idempotente: rieseguibile senza danni. Backfill: le righe
         preesistenti sono tutte EGI-DOC.
@author Padmin D. Curtis (AI Partner OS3.0) for Fabio Cherici
@date 2026-06-01
"""
import os
from pathlib import Path

import dotenv
import psycopg2

dotenv.load_dotenv(Path(__file__).parent / ".env")
SCH = os.getenv("DB_SCHEMA", "stat")


def ensure_schema(conn, log=print):
    """Porta stat.mission_stats allo schema M-220 (organ + PK composta + text).
    Idempotente: no-op se già migrato. Chiamabile dall'ingest così che ogni
    rebuild/ambiente nuovo sia auto-allineato (P1 audit M-220 — no bolt-on)."""
    cur = conn.cursor()

    # 0. mission_id varchar(10) troppo corto per id multi-organo (M-094-SUPERVISOR,
    #    M-OS3-029, ...). Allarga a text. Idempotente (ALTER TYPE è no-op se già text).
    cur.execute(f'alter table "{SCH}".mission_stats alter column mission_id type text')
    cur.execute(f'alter table "{SCH}".mission_stats alter column mission_type type text')

    # 1. colonna organ (idempotente)
    cur.execute(
        "select 1 from information_schema.columns where table_schema=%s "
        "and table_name='mission_stats' and column_name='organ'", (SCH,))
    if not cur.fetchone():
        cur.execute(f'alter table "{SCH}".mission_stats add column organ text')
        log("  organ: colonna aggiunta")

    # 2. backfill righe preesistenti (tutte EGI-DOC) + NOT NULL
    cur.execute(f'update "{SCH}".mission_stats set organ=\'EGI-DOC\' where organ is null')
    if cur.rowcount:
        log(f"  backfill EGI-DOC: {cur.rowcount} righe")
    cur.execute(f'alter table "{SCH}".mission_stats alter column organ set not null')

    # 3. PK → (organ, mission_id)
    cur.execute("""select a.attname from pg_index i
        join pg_attribute a on a.attrelid=i.indrelid and a.attnum=any(i.indkey)
        where i.indrelid=(%s||'.mission_stats')::regclass and i.indisprimary""", (SCH,))
    pk_cols = {r[0] for r in cur.fetchall()}
    if pk_cols != {"organ", "mission_id"}:
        cur.execute("""select conname from pg_constraint
            where conrelid=(%s||'.mission_stats')::regclass and contype='p'""", (SCH,))
        row = cur.fetchone()
        if row:
            cur.execute(f'alter table "{SCH}".mission_stats drop constraint "{row[0]}"')
        cur.execute(f'alter table "{SCH}".mission_stats add primary key (organ, mission_id)')
        log("  PK: (organ, mission_id) creata")

    conn.commit()


def main():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"), port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_DATABASE"), user=os.getenv("DB_USERNAME"),
        password=os.getenv("DB_PASSWORD"), connect_timeout=10,
    )
    ensure_schema(conn)
    conn.close()
    print("  Done.")


if __name__ == "__main__":
    main()
