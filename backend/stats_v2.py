"""
EGI-STAT Statistics Engine v2.0 — Mission-driven metrics (serving).

Source: SQLite locale (data/stats.db) — FONTE UNICA del serving
(SSOT §Principio cardine: la dashboard legge SOLO dallo SQLite locale).
Lo SQLite e popolato dall'aggregatore multi-registry aggregate_to_sqlite.py
(COMMIT -> REGISTRY JSON -> SQLite serving -> dashboard).
La lettura diretta del file di registry JSON (M-167) e DEPRECATA e RIMOSSA:
questo modulo non apre piu nessun registry-file ed e fonte-unica SQLite.

Cognitive Load v2.0 / Productivity Index v2.0 NON sono piu ricalcolati qui:
sono pre-calcolati a monte (aggregatore/enrich) e letti as-is dalle colonne
missions.cognitive_load / missions.productivity_index (single-source: la
verita del calcolo vive in un solo posto).

@author   Padmin D. Curtis (CTO-AI) for Fabio Cherici (CEO)
@version  3.0.0 (FlorenceEGI — EGI-STAT, M-226 S2)
@date     2026-06-03
@purpose  Servire le metriche di produttivita leggendo ESCLUSIVAMENTE dallo
          SQLite locale (fonte unica), mantenendo firme pubbliche e shape JSON
          attese da api.py e dal frontend.
"""

import os
import sqlite3
from collections import defaultdict
from datetime import datetime

# Sorgente UNICA: lo SQLite serving locale (rigenerabile dai registry JSON via
# aggregate_to_sqlite.py). Override per i test via env STATS_DB_PATH.
DB_PATH = os.getenv(
    "STATS_DB_PATH",
    str((__import__("pathlib").Path(__file__).resolve().parent) / "data" / "stats.db"),
)

# Filtro chiusura ESPLICITO (P0-3: nessun default nascosto). Lo SQLite contiene
# SOLO mission completed/closed; conteggiamo come "chiuse" quelle con una data
# di chiusura valida (non NULL, non vuota, non 'pending').
_CLOSED_WHERE = "date_closed IS NOT NULL AND date_closed != '' AND date_closed != 'pending'"


def _connect():
    """Apre lo SQLite serving in sola lettura logica con row_factory dict.

    Se il file non esiste, fallisce in modo esplicito (P0-5): meglio un errore
    parlante che query mute su un DB vuoto creato al volo da sqlite3.connect.
    """
    if not os.path.isfile(DB_PATH):
        raise FileNotFoundError(
            f"SQLite serving assente: {DB_PATH}. "
            "Esegui aggregate_to_sqlite.py per (ri)generarlo dai registry JSON."
        )
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ── Lettura mission (sostituisce completed_missions() file-based) ─────────────
def completed_missions(registry=None):
    """Tutte le mission chiuse dallo SQLite, come lista di dict con la SHAPE
    storica attesa da compute_mission_metrics()/summary_stats().

    Il parametro `registry` e mantenuto per compatibilita di firma ma e IGNORATO
    (non esiste piu lettura registry-file). I tag sono ricostruiti da mission_tags.
    """
    conn = _connect()
    try:
        rows = conn.execute(
            f"""
            SELECT id, title, mission_type, organ, cross_organ,
                   date_opened, date_closed, total_commits, weighted_commits,
                   lines_net, lines_added, lines_deleted, files_touched,
                   cognitive_load, productivity_index
            FROM missions
            WHERE {_CLOSED_WHERE}
            """
        ).fetchall()

        tags_by_mission = defaultdict(dict)
        for t in conn.execute("SELECT mission_id, tag, count FROM mission_tags").fetchall():
            tags_by_mission[t["mission_id"]][t["tag"]] = t["count"]
    finally:
        conn.close()

    out = []
    for r in rows:
        out.append({
            "mission_id": r["id"],
            "titolo": r["title"] or "",
            "tipo_missione": r["mission_type"] or "",
            "organi_coinvolti": [r["organ"]] if r["organ"] else [],
            "cross_organo": bool(r["cross_organ"]),
            "data_apertura": r["date_opened"],
            "data_chiusura": r["date_closed"],
            "stats": {
                "total_commits": r["total_commits"],
                "weighted_commits": r["weighted_commits"],
                "lines_net": r["lines_net"],
                "lines_added": r["lines_added"],
                "lines_deleted": r["lines_deleted"],
                "files_touched": r["files_touched"],
                "tags_breakdown": dict(tags_by_mission.get(r["id"], {})),
                "cognitive_load": r["cognitive_load"],
                "productivity_index": r["productivity_index"],
            },
        })
    return out


def compute_mission_metrics(mission):
    """Mappa una mission (shape di completed_missions) alla metrica v2.0.

    CL/PI sono letti dalle colonne pre-calcolate (single-source), non ricalcolati.
    """
    stats = mission.get("stats", {})
    return {
        "mission_id": mission.get("mission_id"),
        "titolo": mission.get("titolo", ""),
        "tipo": mission.get("tipo_missione", ""),
        "organi": mission.get("organi_coinvolti", []),
        "cross_organo": mission.get("cross_organo", False),
        "data_apertura": mission.get("data_apertura"),
        "data_chiusura": mission.get("data_chiusura"),
        "total_commits": stats.get("total_commits", 0),
        "weighted_commits": stats.get("weighted_commits", 0),
        "lines_net": stats.get("lines_net", 0),
        "lines_added": stats.get("lines_added", 0),
        "lines_deleted": stats.get("lines_deleted", 0),
        "files_touched": stats.get("files_touched", 0),
        "tags_breakdown": stats.get("tags_breakdown", {}),
        "cognitive_load": stats.get("cognitive_load", 0),
        "productivity_index": stats.get("productivity_index", 0),
    }


# ── Aggregazione giornaliera (cuore del fix "settimane recenti zero") ─────────
def aggregate_daily(missions=None):
    """Aggregazione giornaliera dallo SQLite (multi-organo, fonte unica).

    - LAVORO per giorno: SUM su mission_repo_day GROUP BY day (commits/lines/files
      su TUTTI gli organi -> niente piu solo-EGI-DOC, il bug "settimane recenti
      zero" e risolto).
    - CHIUSURE per giorno: aggregazione su missions GROUP BY date_closed
      (count, avg cognitive_load, avg productivity_index, lista mission id).
    - weighted_commits per-giorno: mission_repo_day NON conserva i tag per-day,
      quindi il vecchio calcolo tag-based per-giorno NON e ricostruibile dalla
      fonte unica. weighted_commits e una metrica mission-level: la attribuiamo
      al giorno di CHIUSURA (SUM missions.weighted_commits GROUP BY date_closed).
      Cambio di output rispetto al file-based (Trigger Matrix tipo 2 / DOC-SYNC).

    Il parametro `missions` e mantenuto per compatibilita di firma ma e IGNORATO:
    i dati vengono letti direttamente dallo SQLite.
    """
    conn = _connect()
    try:
        work_rows = conn.execute(
            """
            SELECT day,
                   SUM(commits)                          AS commits,
                   SUM(lines_added)                      AS lines_added,
                   SUM(lines_deleted)                    AS lines_deleted,
                   SUM(lines_added) - SUM(lines_deleted) AS lines_net,
                   SUM(files_touched)                    AS files_touched
            FROM mission_repo_day
            GROUP BY day
            """
        ).fetchall()

        closed_rows = conn.execute(
            f"""
            SELECT date_closed              AS day,
                   COUNT(*)                 AS missions_closed,
                   AVG(cognitive_load)      AS avg_cognitive_load,
                   AVG(productivity_index)  AS avg_productivity_index,
                   SUM(weighted_commits)    AS weighted_commits,
                   GROUP_CONCAT(id)         AS mission_ids
            FROM missions
            WHERE {_CLOSED_WHERE}
            GROUP BY date_closed
            """
        ).fetchall()
    finally:
        conn.close()

    work = {r["day"]: r for r in work_rows}
    closed = {r["day"]: r for r in closed_rows}

    result = []
    all_days = sorted(set(work.keys()) | set(closed.keys()))
    for day in all_days:
        w = work.get(day)
        c = closed.get(day)
        result.append({
            "date": day,
            "commits": w["commits"] if w else 0,
            "weighted_commits": round(c["weighted_commits"], 2) if c and c["weighted_commits"] is not None else 0,
            "lines_net": w["lines_net"] if w else 0,
            "lines_added": w["lines_added"] if w else 0,
            "lines_deleted": w["lines_deleted"] if w else 0,
            "files_touched": w["files_touched"] if w else 0,
            "missions_closed": c["missions_closed"] if c else 0,
            "avg_cognitive_load": round(c["avg_cognitive_load"], 2) if c and c["avg_cognitive_load"] is not None else 0,
            "avg_productivity_index": round(c["avg_productivity_index"], 2) if c and c["avg_productivity_index"] is not None else 0,
            "missions": c["mission_ids"].split(",") if c and c["mission_ids"] else [],
        })
    return result


# ── Periodo (week/month) — INVARIATO: bucketizza il daily ─────────────────────
def _iso_week(date_str):
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    iso = dt.isocalendar()
    return iso[0], iso[1]


def _month_key(date_str):
    return date_str[:7]


def _aggregate_period(daily_data, key_fn):
    """Aggregazione di periodo a partire dai dati daily (logica invariata)."""
    buckets = defaultdict(lambda: {
        "commits": 0, "weighted_commits": 0.0,
        "lines_net": 0, "lines_added": 0, "lines_deleted": 0,
        "files_touched": 0, "missions_closed": 0,
        "cl_sum": 0.0, "pi_sum": 0.0, "cl_count": 0,
    })

    for d in daily_data:
        key = key_fn(d["date"])
        b = buckets[key]
        b["commits"] += d["commits"]
        b["weighted_commits"] += d["weighted_commits"]
        b["lines_net"] += d["lines_net"]
        b["lines_added"] += d["lines_added"]
        b["lines_deleted"] += d["lines_deleted"]
        b["files_touched"] += d["files_touched"]
        b["missions_closed"] += d["missions_closed"]
        if d["missions_closed"] > 0:
            b["cl_sum"] += d["avg_cognitive_load"] * d["missions_closed"]
            b["pi_sum"] += d["avg_productivity_index"] * d["missions_closed"]
            b["cl_count"] += d["missions_closed"]

    result = []
    for key in sorted(buckets.keys()):
        b = buckets[key]
        mc = b["cl_count"] or 1
        is_week = not isinstance(key, str)  # weekly = chiave tupla (year, weeknum); monthly = str
        period = key if isinstance(key, str) else f"{key[0]}-W{key[1]:02d}"
        row = {
            "period": period,
            "commits": b["commits"],
            "weighted_commits": round(b["weighted_commits"], 2),
            "lines_net": b["lines_net"],
            "lines_added": b["lines_added"],
            "lines_deleted": b["lines_deleted"],
            "files_touched": b["files_touched"],
            "missions_closed": b["missions_closed"],
            "avg_cognitive_load": round(b["cl_sum"] / mc, 2),
            "avg_productivity_index": round(b["pi_sum"] / mc, 2),
        }
        # alias 'week' SOLO sul weekly (Pilastro 3: sul monthly sarebbe un month-key fuorviante).
        # Il frontend consuma 'period'; 'week' soddisfa il contratto del test M-226.
        if is_week:
            row["week"] = period
        result.append(row)
    return result


def aggregate_weekly(daily_data=None):
    if daily_data is None:
        daily_data = aggregate_daily()
    return _aggregate_period(daily_data, _iso_week)


def aggregate_monthly(daily_data=None):
    if daily_data is None:
        daily_data = aggregate_daily()
    return _aggregate_period(daily_data, _month_key)


# ── Summary all-time ──────────────────────────────────────────────────────────
def summary_stats(missions=None):
    """Summary complessivo letto dallo SQLite (aggregati SUM/AVG su missions).

    NOTA semantica (DOC-SYNC tipo 2): missions_by_organ conta per organo di
    PROVENIENZA (1 colonna `organ`), non piu per ogni organo coinvolto
    (organi_coinvolti[] multi). Lo SQLite serving non conserva la lista multi-organo.
    """
    conn = _connect()
    try:
        agg = conn.execute(
            f"""
            SELECT COUNT(*)                                   AS total_missions,
                   COALESCE(SUM(total_commits), 0)            AS total_commits,
                   ROUND(COALESCE(SUM(weighted_commits), 0), 2) AS total_weighted_commits,
                   COALESCE(SUM(lines_net), 0)                AS total_lines_net,
                   COALESCE(SUM(files_touched), 0)            AS total_files_touched,
                   ROUND(AVG(cognitive_load), 2)              AS avg_cognitive_load,
                   ROUND(AVG(productivity_index), 2)          AS avg_productivity_index
            FROM missions
            WHERE {_CLOSED_WHERE}
            """
        ).fetchone()

        if not agg or agg["total_missions"] == 0:
            return {}

        by_type = {
            r["mission_type"]: r["n"]
            for r in conn.execute(
                f"SELECT mission_type, COUNT(*) n FROM missions WHERE {_CLOSED_WHERE} GROUP BY mission_type"
            ).fetchall()
        }
        by_organ = {
            r["organ"]: r["n"]
            for r in conn.execute(
                f"SELECT organ, COUNT(*) n FROM missions WHERE {_CLOSED_WHERE} GROUP BY organ"
            ).fetchall()
        }
    finally:
        conn.close()

    return {
        "total_missions": agg["total_missions"],
        "total_commits": agg["total_commits"],
        "total_weighted_commits": agg["total_weighted_commits"],
        "total_lines_net": agg["total_lines_net"],
        "total_files_touched": agg["total_files_touched"],
        "avg_cognitive_load": agg["avg_cognitive_load"],
        "avg_productivity_index": agg["avg_productivity_index"],
        "missions_by_type": by_type,
        "missions_by_organ": by_organ,
    }
