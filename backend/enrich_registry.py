"""
Enrich MISSION_REGISTRY.json with real statistics for each closed mission.

Reads git log from each project directory for the mission's date range,
calculates the same metrics as EGI-STAT (lines, commits, PI, CL),
and writes them directly into the registry JSON.

The registry IS the source of truth. No DB needed.

@author Padmin D. Curtis (AI Partner OS3.0) for Fabio Cherici
@version 1.0.0 (FlorenceEGI — EGI-STAT)
@date 2026-04-08
@purpose Write real stats into MISSION_REGISTRY.json
"""

import json
import math
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REGISTRY_PATH = Path("/home/fabio/EGI-DOC/docs/missions/MISSION_REGISTRY.json")

# All project directories
PROJECT_DIRS = {
    "EGI": "/home/fabio/EGI",
    "EGI-HUB": "/home/fabio/EGI-HUB",
    "EGI-HUB-HOME": "/home/fabio/EGI-HUB-HOME-REACT",
    "EGI-SIGILLO": "/home/fabio/EGI-SIGILLO",
    "EGI-Credential": "/home/fabio/EGI-Credential",
    "NATAN_LOC": "/home/fabio/NATAN_LOC",
    "EGI-INFO": "/home/fabio/EGI-INFO",
    "EGI-DOC": "/home/fabio/EGI-DOC",
    "EGI-STAT": "/home/fabio/EGI-STAT",
    "ecosistema": None,
}

TAG_WEIGHTS = {
    "FEAT": 1.0, "FIX": 1.5, "REFACTOR": 2.0, "TEST": 1.2, "DEBUG": 1.3,
    "DOC": 0.8, "CONFIG": 0.7, "CHORE": 0.6, "I18N": 0.7, "PERF": 1.4,
    "SECURITY": 1.8, "WIP": 0.3, "REVERT": 0.5, "MERGE": 0.4, "DEPLOY": 0.8,
    "UPDATE": 0.6, "UNTAGGED": 0.5, "ARCH": 1.6, "DEBITO": 0.7,
}

MISSION_TYPE_MULTIPLIER = {
    "feature": 1.0, "bugfix": 1.3, "refactor": 1.5,
    "docsync": 0.8, "audit": 1.1, "lso-evolution": 1.5,
}


def parse_tag(message):
    import re
    m = re.match(r'^\[([A-Z_-]+)\]', message)
    if m:
        return m.group(1)
    m = re.match(r'^(feat|fix|refactor|test|docs|chore|perf|ci|build)[\(:]', message, re.I)
    if m:
        t = m.group(1).upper()
        return "DOC" if t == "DOCS" else t
    if message.startswith("Merge "):
        return "MERGE"
    return "UNTAGGED"


def git_log_stats(repo_dir, since, until):
    """Run git log --numstat and return parsed data."""
    try:
        result = subprocess.run(
            ["git", "-C", repo_dir, "log",
             f"--since={since}", f"--until={until} 23:59:59",
             "--pretty=format:%H|%s", "--numstat"],
            capture_output=True, text=True, timeout=30
        )
        return result.stdout.strip()
    except Exception:
        return ""


def calculate_stats_for_mission(mission):
    """Calculate real stats from git log for a mission."""
    organs = mission.get("organi_coinvolti", [])
    date_opened = mission.get("data_apertura")
    date_closed = mission.get("data_chiusura")

    if not date_opened or not date_closed or date_closed == "pending":
        return None

    # Find dirs to scan
    dirs = []
    for organ in organs:
        d = PROJECT_DIRS.get(organ)
        if d and Path(d).exists():
            dirs.append(d)

    if not dirs:
        # If no matching dirs, return stats based on files_modified only
        fm = mission.get("files_modified", [])
        return {
            "total_commits": 0,
            "lines_added": 0,
            "lines_deleted": 0,
            "lines_net": 0,
            "lines_touched": 0,
            "files_touched": len(fm),
            "weighted_commits": 0,
            "cognitive_load": 1.0,
            "productivity_index": 0,
            "tags_breakdown": {},
            "calculated_at": datetime.now().strftime("%Y-%m-%d"),
        }

    total_commits = 0
    lines_added = 0
    lines_deleted = 0
    files_set = set()
    tag_counts = {}

    for repo_dir in dirs:
        log_output = git_log_stats(repo_dir, date_opened, date_closed)
        if not log_output:
            continue

        for line in log_output.split("\n"):
            if not line.strip():
                continue

            # Commit line: hash|message
            if "|" in line:
                parts = line.split("|", 1)
                if len(parts[0]) >= 30:
                    total_commits += 1
                    msg = parts[1] if len(parts) > 1 else ""
                    tag = parse_tag(msg)
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
                    continue

            # Numstat line: added\tdeleted\tfilename
            parts = line.split("\t")
            if len(parts) >= 3:
                added = int(parts[0]) if parts[0] != "-" else 0
                deleted = int(parts[1]) if parts[1] != "-" else 0
                fname = parts[2]
                if fname and "node_modules" not in fname and "vendor" not in fname and "package-lock" not in fname:
                    lines_added += added
                    lines_deleted += deleted
                    files_set.add(fname)

    lines_net = lines_added - lines_deleted
    lines_touched = lines_added + lines_deleted
    files_touched = len(files_set) or len(mission.get("files_modified", []))

    # Weighted commits
    weighted = sum(count * TAG_WEIGHTS.get(tag, 0.5) for tag, count in tag_counts.items())

    # Cognitive load
    cl = 1.0
    if total_commits > 0:
        li = math.log(lines_touched + 1)
        fm = math.log(files_touched + 1)
        dp = math.log(total_commits + 1)
        cl = max(1.0, min(3.5, 1.0 + (li + fm + dp) / 6.0))

    # Productivity index
    mt = MISSION_TYPE_MULTIPLIER.get(mission.get("tipo_missione", "feature"), 1.0)
    capped = min(abs(lines_net), 2000)
    base = (weighted * 10.0) + (capped / 10.0)
    pi = (base * mt) / cl if cl > 0 else 0

    return {
        "total_commits": total_commits,
        "lines_added": lines_added,
        "lines_deleted": lines_deleted,
        "lines_net": lines_net,
        "lines_touched": lines_touched,
        "files_touched": files_touched,
        "weighted_commits": round(weighted, 2),
        "cognitive_load": round(cl, 2),
        "productivity_index": round(pi, 2),
        "tags_breakdown": tag_counts,
        "calculated_at": datetime.now().strftime("%Y-%m-%d"),
    }


def main():
    force = "--force" in sys.argv

    print(f"{'='*70}")
    print(f"  Mission Registry Stats Enrichment — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*70}")

    registry = json.loads(REGISTRY_PATH.read_text())
    enriched = 0

    for mission in registry.get("missions", []):
        if mission.get("stato") != "completed":
            continue
        if not mission.get("titolo"):
            continue
        if mission.get("stats") and not force:
            continue  # already enriched

        stats = calculate_stats_for_mission(mission)
        if stats:
            mission["stats"] = stats
            enriched += 1
            mid = mission["mission_id"]
            s = stats
            print(f"  {mid} | {s['total_commits']:3d} commits | "
                  f"+{s['lines_added']:5d} -{s['lines_deleted']:5d} = {s['lines_net']:+6d} net | "
                  f"{s['files_touched']:3d} files | PI:{s['productivity_index']:7.2f} | "
                  f"{mission.get('titolo','')[:40]}")

    if enriched > 0:
        REGISTRY_PATH.write_text(json.dumps(registry, indent=2, ensure_ascii=False))
        print(f"\n  ✓ {enriched} missions enriched in MISSION_REGISTRY.json")
    else:
        print("  All completed missions already have stats.")

    print(f"{'='*70}")


if __name__ == "__main__":
    main()
