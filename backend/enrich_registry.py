"""
Enrich MISSION_REGISTRY.json with real git statistics for each closed mission.

Two-level output:
  - aggregate totals (total_commits, lines_added, ...) for mission display
  - by_repo_day breakdown: one entry per (github_repo, commit_date) with
    the exact counts from `git log`. That breakdown is the source of truth
    ingest_missions.py writes 1:1 into daily_stats — no split, no GREATEST.

Raw git numbers — no file-type filter. If git reports 3562 lines added on
a given day/repo, we store 3562.

@author Padmin D. Curtis (AI Partner OS3.0) for Fabio Cherici
@version 2.0.0 (FlorenceEGI — EGI-STAT)
@date 2026-04-19
@purpose Write real per-(repo,day) stats into MISSION_REGISTRY.json
"""

import json
import math
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

REGISTRY_PATH = Path("/home/fabio/EGI-DOC/docs/missions/MISSION_REGISTRY.json")

# organ_key → (local_dir, github_repo_name used in daily_stats.repo_name)
PROJECT_REPO = {
    "EGI":                  ("/home/fabio/EGI",                 "florenceegi/EGI"),
    "EGI-HUB":              ("/home/fabio/EGI-HUB",             "florenceegi/EGI-HUB"),
    "EGI-HUB-HOME":         ("/home/fabio/EGI-HUB-HOME-REACT",  "florenceegi/EGI-HUB-HOME-REACT"),
    "EGI-HUB-HOME-REACT":   ("/home/fabio/EGI-HUB-HOME-REACT",  "florenceegi/EGI-HUB-HOME-REACT"),
    "EGI-SIGILLO":          ("/home/fabio/EGI-SIGILLO",         "florenceegi/EGI-SIGILLO"),
    "EGI-Credential":       ("/home/fabio/EGI-Credential",      "florenceegi/egi-credential"),
    "NATAN_LOC":            ("/home/fabio/NATAN_LOC",           "florenceegi/NATAN_LOC"),
    "EGI-INFO":             ("/home/fabio/EGI-INFO",            "florenceegi/EGI-INFO"),
    "EGI-DOC":              ("/home/fabio/EGI-DOC",             "florenceegi/EGI-DOC"),
    "EGI-STAT":             ("/home/fabio/EGI-STAT",            "florenceegi/EGI-STAT"),
    "oracode":              ("/home/fabio/oracode",             "florenceegi/oracode"),
    "YURI-BIAGINI":         ("/home/fabio/YURI-BIAGINI",        "florenceegi/YURI-BIAGINI"),
    "LA-BOTTEGA":           ("/home/fabio/LA-BOTTEGA",          "florenceegi/la-bottega"),
    "La Bottega":           ("/home/fabio/LA-BOTTEGA",          "florenceegi/la-bottega"),
    "FABIO-CHERICI":        ("/home/fabio/FABIO-CHERICI-SITE",  "florenceegi/fabiocherici"),
    "CREATOR-STAGING":      ("/home/fabio/CREATOR-STAGING",     "florenceegi/creator-staging"),
    "GIALLORO-FIRENZE":     ("/home/fabio/GIALLORO-FIRENZE",    "florenceegi/gialloro-firenze"),
    "GIALLORO-FIRENZE-CMS": ("/home/fabio/GIALLORO-FIRENZE-CMS","florenceegi/gialloro-firenze-cms"),
}

# "ecosistema" → no local dir; stats fall back to EGI-DOC
ECOSYSTEM_FALLBACK = ("EGI-DOC", PROJECT_REPO["EGI-DOC"])

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


def _git_log(repo_dir, since, until, files=None):
    """Run git log --numstat with date in format. 1-day buffer on both sides
    to absorb timezone drift. Searches all branches."""
    try:
        d_since = datetime.strptime(since[:10], "%Y-%m-%d") - timedelta(days=1)
        d_until = datetime.strptime(until[:10], "%Y-%m-%d") + timedelta(days=1)
        since_str = d_since.strftime("%Y-%m-%d")
        until_str = d_until.strftime("%Y-%m-%d 23:59:59")
    except Exception:
        since_str, until_str = since, f"{until} 23:59:59"

    cmd = [
        "git", "-C", repo_dir, "log", "--all",
        f"--since={since_str}", f"--until={until_str}",
        "--pretty=format:COMMIT|%H|%ad|%s",
        "--date=short",
        "--numstat",
    ]
    if files:
        clean = [f for f in files if "*" not in f and "~" not in f]
        if not clean:
            return ""
        cmd += ["--"] + clean
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return result.stdout.strip()
    except Exception:
        return ""


def _collect_repo_stats(repo_dir, github_name, since, until, files):
    """Scan one repo and return a list of per-day entries plus the raw hash set.

    entries: dict keyed by (github_name, date_str)
        → {"commits": set(hashes), "added": int, "deleted": int,
           "files": set(filenames), "tags": {tag: count}}
    """
    by_day = {}
    log_output = _git_log(repo_dir, since, until, files)
    if not log_output:
        return by_day

    current_hash = None
    current_date = None
    for line in log_output.split("\n"):
        if not line:
            continue
        if line.startswith("COMMIT|"):
            parts = line.split("|", 3)
            if len(parts) >= 4:
                current_hash = parts[1].strip()
                current_date = parts[2].strip()
                msg = parts[3]
                key = (github_name, current_date)
                slot = by_day.setdefault(key, {
                    "commits": set(), "added": 0, "deleted": 0,
                    "files": set(), "tags": {},
                })
                if current_hash not in slot["commits"]:
                    slot["commits"].add(current_hash)
                    tag = parse_tag(msg)
                    slot["tags"][tag] = slot["tags"].get(tag, 0) + 1
            continue

        # numstat line: "added\tdeleted\tfilename"
        parts = line.split("\t")
        if len(parts) >= 3 and current_hash and current_date:
            added = int(parts[0]) if parts[0].isdigit() else 0
            deleted = int(parts[1]) if parts[1].isdigit() else 0
            fname = parts[2]
            key = (github_name, current_date)
            slot = by_day.get(key)
            if slot is not None:
                slot["added"] += added
                slot["deleted"] += deleted
                if fname:
                    slot["files"].add(fname)
    return by_day


def _mission_target_repos(mission):
    """Resolve the set of (local_dir, github_name) the mission should scan."""
    organs = mission.get("organi_coinvolti", []) or []
    seen = set()
    out = []
    for o in organs:
        if o == "ecosistema":
            organ, mapping = ECOSYSTEM_FALLBACK
        elif o in PROJECT_REPO:
            organ, mapping = o, PROJECT_REPO[o]
        else:
            continue
        local_dir, github_name = mapping
        if github_name in seen:
            continue
        if not Path(local_dir).exists():
            continue
        seen.add(github_name)
        out.append((local_dir, github_name))
    return out


def calculate_stats_for_mission(mission):
    """Produce aggregate + by_repo_day breakdown using raw git numbers."""
    date_opened = mission.get("data_apertura")
    date_closed = mission.get("data_chiusura")
    files_modified = mission.get("files_modified", []) or []

    if not date_opened or not date_closed or date_closed == "pending":
        return None

    targets = _mission_target_repos(mission)
    if not targets:
        return {
            "total_commits": 0, "lines_added": 0, "lines_deleted": 0,
            "lines_net": 0, "lines_touched": 0, "files_touched": len(files_modified),
            "weighted_commits": 0, "cognitive_load": 1.0, "productivity_index": 0,
            "tags_breakdown": {}, "by_repo_day": [], "commit_hashes": [],
            "calculated_at": datetime.now().strftime("%Y-%m-%d"),
        }

    merged = {}
    for local_dir, github_name in targets:
        repo_files = None
        if files_modified:
            cleaned = []
            for f in files_modified:
                c = f
                for prefix in [
                    "EGI-DOC/", "EGI-STAT/", "~/.claude/", "oracode/",
                    "YURI-BIAGINI/", "EGI/", "EGI-HUB/", "EGI-Credential/",
                    "EGI-SIGILLO/", "EGI-HUB-HOME-REACT/", "EGI-INFO/",
                    "NATAN_LOC/", "GIALLORO-FIRENZE/", "GIALLORO-FIRENZE-CMS/",
                    "CREATOR-STAGING/", "LA-BOTTEGA/", "FABIO-CHERICI-SITE/",
                ]:
                    if c.startswith(prefix):
                        c = c[len(prefix):]
                cleaned.append(c)
            repo_files = cleaned
        by_day = _collect_repo_stats(local_dir, github_name, date_opened, date_closed, repo_files)
        for key, slot in by_day.items():
            dst = merged.setdefault(key, {
                "commits": set(), "added": 0, "deleted": 0,
                "files": set(), "tags": {},
            })
            dst["commits"] |= slot["commits"]
            dst["added"] += slot["added"]
            dst["deleted"] += slot["deleted"]
            dst["files"] |= slot["files"]
            for tag, count in slot["tags"].items():
                dst["tags"][tag] = dst["tags"].get(tag, 0) + count

    # Build by_repo_day list + aggregate totals
    by_repo_day = []
    all_hashes = set()
    agg_added = agg_deleted = 0
    agg_files = set()
    agg_tags = {}
    for (repo_name, date_str), slot in sorted(merged.items()):
        commits_count = len(slot["commits"])
        by_repo_day.append({
            "repo": repo_name,
            "date": date_str,
            "commits": commits_count,
            "lines_added": slot["added"],
            "lines_deleted": slot["deleted"],
            "files_touched": len(slot["files"]),
            "tags": slot["tags"],
        })
        all_hashes |= slot["commits"]
        agg_added += slot["added"]
        agg_deleted += slot["deleted"]
        agg_files |= slot["files"]
        for tag, count in slot["tags"].items():
            agg_tags[tag] = agg_tags.get(tag, 0) + count

    total_commits = len(all_hashes)
    lines_added = agg_added
    lines_deleted = agg_deleted
    lines_net = lines_added - lines_deleted
    lines_touched = lines_added + lines_deleted
    files_touched = len(agg_files) or len(files_modified)

    weighted = sum(count * TAG_WEIGHTS.get(tag, 0.5) for tag, count in agg_tags.items())

    cl = 1.0
    if total_commits > 0:
        li = math.log(lines_touched + 1)
        fm = math.log(files_touched + 1)
        dp = math.log(total_commits + 1)
        cl = max(1.0, min(3.5, 1.0 + (li + fm + dp) / 6.0))

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
        "tags_breakdown": agg_tags,
        "commit_hashes": sorted(all_hashes),
        "by_repo_day": by_repo_day,
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
            continue

        stats = calculate_stats_for_mission(mission)
        if stats:
            mission["stats"] = stats
            enriched += 1
            mid = mission["mission_id"]
            s = stats
            repos = {e["repo"] for e in s["by_repo_day"]}
            print(f"  {mid} | {s['total_commits']:3d} commits | "
                  f"+{s['lines_added']:6d} -{s['lines_deleted']:5d} = {s['lines_net']:+7d} net | "
                  f"{s['files_touched']:3d} files | {len(repos)} repos | PI:{s['productivity_index']:7.2f} | "
                  f"{mission.get('titolo','')[:40]}")

    if enriched > 0:
        REGISTRY_PATH.write_text(json.dumps(registry, indent=2, ensure_ascii=False))
        print(f"\n  ✓ {enriched} missions enriched in MISSION_REGISTRY.json")
    else:
        print("  All completed missions already have stats.")

    print(f"{'='*70}")


if __name__ == "__main__":
    main()
