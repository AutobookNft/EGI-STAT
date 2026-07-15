"""
@package  EGI-STAT/backend/tests
@author   Padmin D. Curtis (Supervisor-CTO, AI Partner OS3.0) for Fabio Cherici
@version  1.0.0 (FlorenceEGI — EGI-STAT, M-NXC-001)
@date     2026-07-16
@purpose  Test RED M-NXC-001 (porta EGI-STAT): l'aggregatore che COSTRUISCE lo
  stats.db spedito al server nexus deve popolare le tabelle value_daily/value_weekly
  (produzione a VALORE), altrimenti il DB spedito non le contiene e i grafici del
  cockpit — che le LEGGONO via stats_v2.value_series — restano vuoti.
  Contratto (identico per schema/semantica alla copia nexus-cockpit):
   - schema: value_daily + value_weekly con le 9 colonne (period PK, n_create,
     create_score, n_sync, n_errori, error_penalty, net_score, per_livello,
     sync_per_livello). period = PK => idempotenza per full-rebuild.
   - popolamento riusando os3-matrix bin/production_index.py (DRY, NON riscritto):
     discovery del registro-capacità (docs/lso/SSOT_REGISTRY.json) via lo STESSO
     meccanismo delle mission-registry, persistenza in SQLite.
   - INVARIANTE §4/§5/§7 (modello Hubbard): net_score == create_score - error_penalty
     per OGNI riga, in entrambe le granularità.
   - RICONCILIAZIONE granularità: la settimana ISO aggrega i suoi giorni — per ogni
     settimana, somma(n_create daily nei giorni di quella settimana) == n_create weekly.
     Proprietà robusta (non numeri live hardcoded): garantisce che i due gemelli
     nascano dalla STESSA serie di eventi, solo maglia temporale diversa.
"""
import os
import sys
import sqlite3
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import aggregate_to_sqlite as agg  # noqa: E402


VALUE_COLS = {
    "period", "n_create", "create_score", "n_sync", "n_errori",
    "error_penalty", "net_score", "per_livello", "sync_per_livello",
}


# ---- schema: le due tabelle value esistono con le colonne attese ----
def test_value_tables_in_schema(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "t.db"))
    agg.create_schema(conn)
    for table in ("value_daily", "value_weekly"):
        cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
        assert VALUE_COLS <= cols, f"schema {table} incompleto: mancano {VALUE_COLS - cols}"
        # period è PK (idempotenza full-rebuild)
        pk = [r[1] for r in conn.execute(f"PRAGMA table_info({table})") if r[5]]
        assert pk == ["period"], f"{table}: period deve essere PK singola, trovato {pk}"


# ---- DROP_TABLES le include (full-rebuild ricostruisce anche le value) ----
def test_value_tables_dropped_on_rebuild():
    assert "value_daily" in agg.DROP_TABLES
    assert "value_weekly" in agg.DROP_TABLES


# ---- build reale: le tabelle value sono POPOLATE dal registro-capacità os3-matrix ----
def test_value_tables_populated_real_build(tmp_path):
    db = str(tmp_path / "real.db")
    agg.aggregate(db)
    conn = sqlite3.connect(db)
    n_weekly = conn.execute("SELECT COUNT(*) FROM value_weekly").fetchone()[0]
    n_daily = conn.execute("SELECT COUNT(*) FROM value_daily").fetchone()[0]
    assert n_weekly > 0, "value_weekly vuota: la porta non popola dal registro-capacità"
    assert n_daily > 0, "value_daily vuota: la porta non popola dal registro-capacità"


# ---- INVARIANTE §4/§5/§7: net_score == create_score - error_penalty su OGNI riga ----
def test_net_score_invariant(tmp_path):
    db = str(tmp_path / "real.db")
    agg.aggregate(db)
    conn = sqlite3.connect(db)
    for table in ("value_daily", "value_weekly"):
        bad = conn.execute(
            f"SELECT period, net_score, create_score, error_penalty FROM {table} "
            f"WHERE net_score != create_score - error_penalty"
        ).fetchall()
        assert not bad, f"{table}: net_score != create_score - error_penalty su {bad}"


# ---- RICONCILIAZIONE: la settimana ISO aggrega i suoi giorni (stessa serie eventi) ----
def test_weekly_reconciles_daily(tmp_path):
    db = str(tmp_path / "real.db")
    agg.aggregate(db)
    conn = sqlite3.connect(db)
    weekly = {p: c for p, c in conn.execute("SELECT period, n_create FROM value_weekly")}
    daily_by_week = {}
    for period, n_create in conn.execute("SELECT period, n_create FROM value_daily"):
        y, m, d = (int(x) for x in period.split("-"))
        iso_year, iso_week, _ = date(y, m, d).isocalendar()
        key = f"{iso_year}-W{iso_week:02d}"
        daily_by_week[key] = daily_by_week.get(key, 0) + n_create
    for week, total in daily_by_week.items():
        assert weekly.get(week, 0) == total, (
            f"settimana {week}: somma daily n_create={total} != weekly n_create={weekly.get(week)}"
        )
