"""
EGI-STAT Statistics Engine v2.0 — Mission-driven metrics.

Source: MISSION_REGISTRY.json (single source of truth).
Algorithms: Cognitive Load v2.0, Productivity Index v2.0.
Aggregation: daily, weekly, monthly from by_repo_day + mission closure dates.

@author Padmin D. Curtis (AI Partner OS3.0) for Fabio Cherici
@version 2.0.0 (FlorenceEGI — EGI-STAT)
@date 2026-05-10
@purpose Compute real productivity metrics from mission registry data
"""

import json
import math
import os
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

REGISTRY_PATH = Path(
    os.getenv("MISSION_REGISTRY_PATH",
              "/home/fabio/EGI-DOC/docs/missions/MISSION_REGISTRY.json")
)

MISSION_TYPE_COMPLEXITY = {
    "refactor": 0.5,
    "bugfix": 0.4,
    "lso-evolution": 0.4,
    "strutturale": 0.4,
    "audit": 0.3,
    "security": 0.3,
    "security-hardening": 0.3,
    "feature": 0.2,
    "performance": 0.3,
    "docsync": 0.1,
    "doc": 0.1,
    "research": 0.15,
}

MISSION_TYPE_MULTIPLIER = {
    "feature": 1.0,
    "bugfix": 1.3,
    "refactor": 1.5,
    "docsync": 0.8,
    "audit": 1.1,
    "lso-evolution": 1.5,
    "strutturale": 1.3,
    "security": 1.4,
    "security-hardening": 1.4,
    "performance": 1.3,
    "research": 0.7,
    "doc": 0.8,
}

PRODUCTIVE_TAGS = {"FEAT", "REFACTOR", "PERF", "SECURITY", "TEST", "ARCH"}

TAG_WEIGHTS = {
    "FEAT": 1.0, "FIX": 1.5, "REFACTOR": 2.0, "TEST": 1.2, "DEBUG": 1.3,
    "DOC": 0.8, "CONFIG": 0.7, "CHORE": 0.6, "I18N": 0.7, "PERF": 1.4,
    "SECURITY": 1.8, "WIP": 0.3, "REVERT": 0.5, "MERGE": 0.4, "DEPLOY": 0.8,
    "UPDATE": 0.6, "UNTAGGED": 0.5, "ARCH": 1.6, "DEBITO": 0.7, "MISSION": 1.2,
}


def load_registry():
    return json.loads(REGISTRY_PATH.read_text())


def completed_missions(registry=None):
    if registry is None:
        registry = load_registry()
    return [
        m for m in registry.get("missions", [])
        if m.get("stato") == "completed"
        and m.get("stats")
        and m.get("data_chiusura") not in (None, "pending")
    ]


def cognitive_load_v2(mission):
    """Cognitive Load v2.0 — 5 dimensions of real complexity."""
    stats = mission.get("stats", {})
    organs = mission.get("organi_coinvolti", []) or []
    cross = mission.get("cross_organo", False)
    tags = stats.get("tags_breakdown", {})
    files_touched = stats.get("files_touched", 0)
    total_commits = stats.get("total_commits", 0)
    files_modified = mission.get("files_modified", [])
    tipo = mission.get("tipo_missione", "feature")

    organ_count = len(set(organs))
    if organ_count <= 1:
        scope = 0.0
    elif organ_count == 2:
        scope = 0.4
    else:
        scope = 0.7
    if cross:
        scope = min(scope + 0.3, 1.0)

    if files_modified and len(files_modified) > 0:
        dirs = set()
        for f in files_modified:
            parts = f.split("/")
            if len(parts) > 1:
                dirs.add("/".join(parts[:2]))
            else:
                dirs.add(parts[0])
        dispersion = min(len(dirs) / max(len(files_modified), 1), 1.0)
    else:
        dispersion = min(files_touched / max(total_commits, 1) / 10, 1.0)

    tag_count = len(tags)
    switching = min(tag_count, 5) / 5.0

    scale = min(math.log2(files_touched + total_commits + 1) / 10.0, 1.0)

    type_factor = MISSION_TYPE_COMPLEXITY.get(tipo, 0.2)

    cl = 1.0 + (
        scope * 0.5
        + dispersion * 0.4
        + switching * 0.3
        + scale * 0.3
        + type_factor * 0.5
    )
    return round(min(cl, 3.5), 2)


def productivity_index_v2(mission, cl=None):
    """Productivity Index v2.0 — value delivered, not volume."""
    stats = mission.get("stats", {})
    tipo = mission.get("tipo_missione", "feature")
    tags = stats.get("tags_breakdown", {})
    weighted = stats.get("weighted_commits", 0)
    lines_net = stats.get("lines_net", 0)

    if cl is None:
        cl = cognitive_load_v2(mission)

    type_mult = MISSION_TYPE_MULTIPLIER.get(tipo, 1.0)
    delivery = weighted * type_mult

    net_impact = min(abs(lines_net), 3000) / 100.0

    total_tags = sum(tags.values()) or 1
    productive = sum(tags.get(t, 0) for t in PRODUCTIVE_TAGS)
    quality = 0.7 + 0.6 * (productive / total_tags)

    pi = (delivery * 10 + net_impact) * quality / cl
    return round(pi, 2)


def compute_mission_metrics(mission):
    """Compute v2.0 metrics for a single mission."""
    stats = mission.get("stats", {})
    cl = cognitive_load_v2(mission)
    pi = productivity_index_v2(mission, cl)

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
        "cognitive_load": cl,
        "productivity_index": pi,
    }


def aggregate_daily(missions=None):
    """Daily aggregation from mission by_repo_day + closure metrics."""
    if missions is None:
        missions = completed_missions()

    daily_work = defaultdict(lambda: {
        "commits": 0, "weighted_commits": 0.0,
        "lines_added": 0, "lines_deleted": 0, "lines_net": 0,
        "files_touched": 0,
    })
    daily_missions_closed = defaultdict(list)

    for m in missions:
        stats = m.get("stats", {})
        cl = cognitive_load_v2(m)
        pi = productivity_index_v2(m, cl)

        for entry in stats.get("by_repo_day", []):
            day = entry.get("date")
            if not day:
                continue
            d = daily_work[day]
            d["commits"] += entry.get("commits", 0)
            la = entry.get("lines_added", 0)
            ld = entry.get("lines_deleted", 0)
            d["lines_added"] += la
            d["lines_deleted"] += ld
            d["lines_net"] += la - ld
            d["files_touched"] += entry.get("files_touched", 0)
            tags = entry.get("tags", {})
            for tag, count in tags.items():
                d["weighted_commits"] += count * TAG_WEIGHTS.get(tag, 0.5)

        closure = m.get("data_chiusura")
        if closure and closure != "pending":
            daily_missions_closed[closure].append({
                "mission_id": m.get("mission_id"),
                "tipo": m.get("tipo_missione"),
                "cognitive_load": cl,
                "productivity_index": pi,
                "weighted_commits": stats.get("weighted_commits", 0),
            })

    result = []
    all_days = sorted(set(daily_work.keys()) | set(daily_missions_closed.keys()))
    for day in all_days:
        work = daily_work.get(day, {
            "commits": 0, "weighted_commits": 0, "lines_added": 0,
            "lines_deleted": 0, "lines_net": 0, "files_touched": 0,
        })
        closed = daily_missions_closed.get(day, [])
        avg_cl = (
            sum(c["cognitive_load"] for c in closed) / len(closed)
            if closed else 0
        )
        avg_pi = (
            sum(c["productivity_index"] for c in closed) / len(closed)
            if closed else 0
        )
        result.append({
            "date": day,
            "commits": work["commits"],
            "weighted_commits": round(work["weighted_commits"], 2),
            "lines_net": work["lines_net"],
            "lines_added": work["lines_added"],
            "lines_deleted": work["lines_deleted"],
            "files_touched": work["files_touched"],
            "missions_closed": len(closed),
            "avg_cognitive_load": round(avg_cl, 2),
            "avg_productivity_index": round(avg_pi, 2),
            "missions": [c["mission_id"] for c in closed],
        })
    return result


def _iso_week(date_str):
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    iso = dt.isocalendar()
    return iso[0], iso[1]


def _month_key(date_str):
    return date_str[:7]


def _aggregate_period(daily_data, key_fn):
    """Generic period aggregation from daily data."""
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
        result.append({
            "period": key if isinstance(key, str) else f"{key[0]}-W{key[1]:02d}",
            "commits": b["commits"],
            "weighted_commits": round(b["weighted_commits"], 2),
            "lines_net": b["lines_net"],
            "lines_added": b["lines_added"],
            "lines_deleted": b["lines_deleted"],
            "files_touched": b["files_touched"],
            "missions_closed": b["missions_closed"],
            "avg_cognitive_load": round(b["cl_sum"] / mc, 2),
            "avg_productivity_index": round(b["pi_sum"] / mc, 2),
        })
    return result


def aggregate_weekly(daily_data=None):
    if daily_data is None:
        daily_data = aggregate_daily()
    return _aggregate_period(daily_data, _iso_week)


def aggregate_monthly(daily_data=None):
    if daily_data is None:
        daily_data = aggregate_daily()
    return _aggregate_period(daily_data, _month_key)


def summary_stats(missions=None):
    """Overall summary across all completed missions."""
    if missions is None:
        missions = completed_missions()

    metrics = [compute_mission_metrics(m) for m in missions]
    if not metrics:
        return {}

    total = len(metrics)
    return {
        "total_missions": total,
        "total_commits": sum(m["total_commits"] for m in metrics),
        "total_weighted_commits": round(sum(m["weighted_commits"] for m in metrics), 2),
        "total_lines_net": sum(m["lines_net"] for m in metrics),
        "total_files_touched": sum(m["files_touched"] for m in metrics),
        "avg_cognitive_load": round(
            sum(m["cognitive_load"] for m in metrics) / total, 2
        ),
        "avg_productivity_index": round(
            sum(m["productivity_index"] for m in metrics) / total, 2
        ),
        "missions_by_type": _count_by(metrics, "tipo"),
        "missions_by_organ": _count_organs(metrics),
    }


def _count_by(metrics, field):
    counts = defaultdict(int)
    for m in metrics:
        counts[m[field]] += 1
    return dict(counts)


def _count_organs(metrics):
    counts = defaultdict(int)
    for m in metrics:
        for o in m.get("organi", []):
            counts[o] += 1
    return dict(counts)
