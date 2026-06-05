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
        # M-OS3-082: time-series = lavoro-mission (mission_repo_day) UNITO al pregresso storico
        # (legacy_repo_day, commit non-mission) → i grafici si estendono ai primi commit (2023+).
        # Additivo: se legacy_repo_day non esiste (ingest non eseguito), si degrada al solo mission.
        has_legacy = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='legacy_repo_day'"
        ).fetchone() is not None
        src = "mission_repo_day"
        if has_legacy:
            src = ("(SELECT day,commits,lines_added,lines_deleted,files_touched FROM mission_repo_day "
                   "UNION ALL SELECT day,commits,lines_added,lines_deleted,files_touched FROM legacy_repo_day)")
        work_rows = conn.execute(
            f"""
            SELECT day,
                   SUM(commits)                          AS commits,
                   SUM(lines_added)                      AS lines_added,
                   SUM(lines_deleted)                    AS lines_deleted,
                   SUM(lines_added) - SUM(lines_deleted) AS lines_net,
                   SUM(files_touched)                    AS files_touched
            FROM {src}
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


# ── Dettaglio giornaliero MISSION-ONLY (M-229) ────────────────────────────────
# Mappa tag-dominante -> emoji. I tag sono quelli del registry mission (mission_tags).
_TAG_ICON = {
    "FEAT": "🚀",
    "FIX": "🐛",
    "REFACTOR": "♻️",
    "DOC": "📖",
    "TEST": "✅",
    "ARCH": "🏛️",
}
_DEFAULT_ICON = "🎯"


def _dominant_tag(tag_counts):
    """Tag dominante (count massimo) da un dict {tag: count}; None se vuoto.

    Tie-break deterministico: a parità di count vince il tag alfabeticamente
    minore (Pilastro 3: output riproducibile, niente ordine d'inserimento).
    """
    if not tag_counts:
        return None
    return max(sorted(tag_counts.keys()), key=lambda t: tag_counts[t])


def daily_detail(date_str):
    """Dettaglio MISSION-ONLY di un singolo giorno, letto SOLO dallo SQLite.

    Fonte unica: mission_repo_day (lavoro per repo/giorno) + missions (CL/PI, tag).
    "Mission attive quel giorno" = mission con almeno una riga in mission_repo_day
    per `date_str` (Principio di esclusività mission: se non passa da una mission,
    non conta — quindi il giorno È definito dal lavoro-mission registrato).

    Shape ritornata:
      { "date", "summary": {...}, "repositories": [ {...}, ... ] }

    Garanzia di contratto (test M-229):
      sum(repositories[].commits) == SUM(mission_repo_day.commits) per quel giorno.

    P0-3 (Statistics Rule): nessun default nascosto. coding_hours/testing_hours
    sono 0.0 ESPLICITO — il modello mission non traccia ore, dichiararlo onesto
    è preferibile a stimarle. Ogni campo numerico è float/int, mai None.
    """
    conn = _connect()
    try:
        repo_rows = conn.execute(
            """
            SELECT repo                                  AS repo_name,
                   SUM(commits)                          AS total_commits,
                   SUM(lines_added)                      AS lines_added,
                   SUM(lines_deleted)                    AS lines_deleted,
                   SUM(lines_added) - SUM(lines_deleted) AS net_lines,
                   SUM(files_touched)                    AS files_touched
            FROM mission_repo_day
            WHERE day = ?
            GROUP BY repo
            ORDER BY repo
            """,
            (date_str,),
        ).fetchall()

        # Per ogni repo: quali mission lo toccano quel giorno (per medie CL/PI e tag).
        repo_missions = defaultdict(set)
        all_mission_ids = set()
        for r in conn.execute(
            "SELECT DISTINCT mission_id, repo FROM mission_repo_day WHERE day = ?",
            (date_str,),
        ).fetchall():
            repo_missions[r["repo"]].add(r["mission_id"])
            all_mission_ids.add(r["mission_id"])

        # CL/PI per mission (pre-calcolati, single-source) e tag per mission.
        mission_cl = {}
        mission_pi = {}
        if all_mission_ids:
            qmarks = ",".join("?" * len(all_mission_ids))
            ids = list(all_mission_ids)
            for m in conn.execute(
                f"SELECT id, cognitive_load, productivity_index FROM missions WHERE id IN ({qmarks})",
                ids,
            ).fetchall():
                mission_cl[m["id"]] = m["cognitive_load"]
                mission_pi[m["id"]] = m["productivity_index"]

            tags_by_mission = defaultdict(lambda: defaultdict(int))
            for t in conn.execute(
                f"SELECT mission_id, tag, count FROM mission_tags WHERE mission_id IN ({qmarks})",
                ids,
            ).fetchall():
                tags_by_mission[t["mission_id"]][t["tag"]] += t["count"]
        else:
            tags_by_mission = {}
    finally:
        conn.close()

    def _avg(values):
        vals = [v for v in values if v is not None]
        return round(sum(vals) / len(vals), 2) if vals else 0.0

    repositories = []
    sum_commits = 0
    sum_weighted = 0.0
    sum_added = 0
    sum_deleted = 0
    sum_net = 0
    sum_files = 0
    day_tag_counts = defaultdict(int)
    cl_all = []
    pi_all = []

    for rr in repo_rows:
        repo = rr["repo_name"]
        mids = repo_missions.get(repo, set())

        cl = _avg([mission_cl.get(m) for m in mids])
        pi = _avg([mission_pi.get(m) for m in mids])

        # weighted_commits per repo: il modello mission non conserva i pesi
        # per-repo-giorno; usiamo i commit grezzi (peso 1) come proxy onesto.
        weighted = float(rr["total_commits"] or 0)

        # tag dominante del lavoro-mission di questo repo nel giorno
        repo_tag_counts = defaultdict(int)
        for m in mids:
            for tag, cnt in tags_by_mission.get(m, {}).items():
                repo_tag_counts[tag] += cnt
                day_tag_counts[tag] += cnt
        dom = _dominant_tag(repo_tag_counts)
        day_type = dom if dom else "mission"
        icon = _TAG_ICON.get(dom, _DEFAULT_ICON)

        commits = int(rr["total_commits"] or 0)
        added = int(rr["lines_added"] or 0)
        deleted = int(rr["lines_deleted"] or 0)
        net = int(rr["net_lines"] or 0)
        files = int(rr["files_touched"] or 0)

        repositories.append({
            "repo_name": repo,
            "commits": commits,          # alias contrattuale (== total_commits)
            "total_commits": commits,
            "lines_added": added,
            "lines_deleted": deleted,
            "net_lines": net,
            "files_touched": files,
            "weighted_commits": round(weighted, 2),
            "cognitive_load": cl,
            "productivity_score": pi,
            "day_type": day_type,
            "day_type_icon": icon,
        })

        sum_commits += commits
        sum_weighted += weighted
        sum_added += added
        sum_deleted += deleted
        sum_net += net
        sum_files += files
        cl_all.extend(mission_cl.get(m) for m in mids)
        pi_all.extend(mission_pi.get(m) for m in mids)

    # Medie a livello giorno: sulle mission DISTINTE attive quel giorno (non
    # pesate sul numero di repo toccati), coerenti con missions_count.
    distinct_cl = [mission_cl.get(m) for m in all_mission_ids]
    distinct_pi = [mission_pi.get(m) for m in all_mission_ids]
    day_dom = _dominant_tag(day_tag_counts)
    summary = {
        "total_commits": sum_commits,
        "weighted_commits": round(sum_weighted, 2),
        "lines_added": sum_added,
        "lines_deleted": sum_deleted,
        "net_lines": sum_net,
        "files_touched": sum_files,
        "cognitive_load": _avg(distinct_cl),
        "productivity_score": _avg(distinct_pi),
        # Onesto (P0-3): il modello mission non traccia le ore -> 0.0 esplicito.
        "coding_hours": 0.0,
        "testing_hours": 0.0,
        "day_type": day_dom if day_dom else "mission",
        "day_type_icon": _TAG_ICON.get(day_dom, _DEFAULT_ICON),
        "missions_count": len(all_mission_ids),
    }

    return {
        "date": date_str,
        "summary": summary,
        "repositories": repositories,
    }


# ── Asse ORE per progetto (M-234) ─────────────────────────────────────────────
def hours_by_project():
    """Ore per progetto dallo SQLite serving (tabella time_entries — M-234).

    Aggrega SUM(minutes) GROUP BY project separando manual/commit (P0-3:
    parametri statistici espliciti, nessun default nascosto). manual = dato
    reale CEO; commit = stima-euristica sui commit-mission. La distinzione
    e ESPLICITA nello shape (manual_minutes vs commit_minutes) per onesta
    epistemica: mai presentare la stima-commit come ore reali.
    """
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT project,
                   COALESCE(SUM(minutes), 0)                                          AS total_minutes,
                   COALESCE(SUM(CASE WHEN source='manual' THEN minutes ELSE 0 END), 0) AS manual_minutes,
                   COALESCE(SUM(CASE WHEN source='commit' THEN minutes ELSE 0 END), 0) AS commit_minutes
            FROM time_entries
            GROUP BY project
            ORDER BY total_minutes DESC
            """
        ).fetchall()
    finally:
        conn.close()

    out = []
    for r in rows:
        tot = r["total_minutes"] or 0
        out.append({
            "project": r["project"],
            "minutes": tot,
            "hours": round(tot / 60.0, 2),
            "manual_minutes": r["manual_minutes"] or 0,
            "commit_minutes": r["commit_minutes"] or 0,
        })
    return out


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
        mission_added = conn.execute(
            f"SELECT COALESCE(SUM(lines_added),0) la, COALESCE(SUM(lines_added)-SUM(lines_deleted),0) ln FROM missions WHERE {_CLOSED_WHERE}"
        ).fetchone()
        # ── Produzione STORICA legacy (M-OS3-081): commit pre/non-mission, per organo. ──
        # Additivo: NON altera i conteggi mission (policy: da ora conta solo il lavoro in mission).
        # È il record storico (commit = fonte di verità) della produzione totale di Florence EGI Srl.
        legacy_by_organ = {}; leg_c = leg_a = leg_n = 0
        try:
            for r in conn.execute(
                "SELECT organ, commits, lines_added, lines_net FROM legacy_production ORDER BY lines_added DESC"
            ).fetchall():
                legacy_by_organ[r["organ"]] = {"commits": r["commits"], "lines_added": r["lines_added"], "lines_net": r["lines_net"]}
                leg_c += r["commits"] or 0; leg_a += r["lines_added"] or 0; leg_n += r["lines_net"] or 0
        except sqlite3.OperationalError:
            pass  # tabella assente → degrada pulito
    finally:
        conn.close()

    m_added = mission_added["la"] if mission_added else 0
    m_net = mission_added["ln"] if mission_added else 0
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
        # ── Asse storico (additivo, M-OS3-081) ──
        "legacy_commits": leg_c,
        "legacy_lines_added": leg_a,
        "legacy_lines_net": leg_n,
        "legacy_by_organ": legacy_by_organ,
        # Produzione TOTALE = mission + legacy (prova storica commit-based)
        "total_production_commits": (agg["total_commits"] or 0) + leg_c,
        "total_production_lines_added": m_added + leg_a,
        "total_production_lines_net": m_net + leg_n,
    }
