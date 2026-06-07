"""
Mission Registry → daily_stats / weekly_stats — v5.0

Writes REAL git numbers into daily_stats. No split. No aggregate-on-closure-day.
No GREATEST arbitrary. For every (repo, date) cell referenced by any mission
in the registry, this script runs `git log` locally and writes whatever git
reports for that day on that repo — period.

daily_stats.(repo, date) = `git log --numstat --since=date --until=date+1`
                                   applied to the local clone, counting
                                   distinct commit hashes and summing
                                   additions / deletions / files.

The mission registry provides the *list of cells* to refresh (any cell touched
by at least one closed mission). Cells outside mission coverage remain managed
by ingest_to_remotedb.py (GitHub API ingester).

@author Padmin D. Curtis (AI Partner OS3.0) for Fabio Cherici
@version 5.0.0 (FlorenceEGI — EGI-STAT)
@date 2026-04-19
@purpose Write REAL per-(repo, date) git stats into daily_stats. Reality only.
"""

import json
import math
import os
import re
import subprocess
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import dotenv
import psycopg2
from psycopg2.extras import Json

import ecosystem  # M-220: discovery multi-registry + normalizzazione 2-schemi
from migrate_mission_stats_organ import ensure_schema  # M-220: auto-migrazione schema

dotenv.load_dotenv(Path(__file__).parent / ".env")

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_DATABASE")
DB_USER = os.getenv("DB_USERNAME")
DB_PASS = os.getenv("DB_PASSWORD")
DB_SCHEMA = os.getenv("DB_SCHEMA", "stat")

REGISTRY_PATH = os.getenv(
    "MISSION_REGISTRY_PATH",
    "/home/fabio/EGI-DOC/docs/missions/MISSION_REGISTRY.json",
)

# github_repo_name → local clone path
REPO_TO_DIR = {
    "florenceegi/EGI":                  "/home/fabio/EGI",
    "florenceegi/EGI-HUB":              "/home/fabio/EGI-HUB",
    "florenceegi/EGI-HUB-HOME-REACT":   "/home/fabio/EGI-HUB-HOME-REACT",
    "florenceegi/EGI-SIGILLO":          "/home/fabio/EGI-SIGILLO",
    "florenceegi/egi-credential":       "/home/fabio/EGI-Credential",
    "florenceegi/NATAN_LOC":            "/home/fabio/NATAN_LOC",
    "florenceegi/EGI-INFO":             "/home/fabio/EGI-INFO",
    "florenceegi/EGI-DOC":              "/home/fabio/EGI-DOC",
    "florenceegi/EGI-STAT":             "/home/fabio/EGI-STAT",
    "florenceegi/oracode":              "/home/fabio/oracode",
    "florenceegi/YURI-BIAGINI":         "/home/fabio/YURI-BIAGINI",
    "florenceegi/la-bottega":           "/home/fabio/LA-BOTTEGA",
    "florenceegi/fabiocherici":         "/home/fabio/fabiocherici.com",
    "florenceegi/creator-staging":      "/home/fabio/CREATOR-STAGING",
    "florenceegi/gialloro-firenze":     "/home/fabio/GIALLORO-FIRENZE",
    "florenceegi/gialloro-firenze-cms": "/home/fabio/GIALLORO-FIRENZE-CMS",
    # M-222: pinocapasso/le-vespe-cafe/os3-matrix NON sono qui di proposito.
    # I loro daily_stats vengono da ingest_to_remotedb (GitHub API, sempre fresco).
    # Metterli qui attiverebbe l'overwrite git-LOCALE (cloni stale → sottoconta)
    # alla prima cella by_repo_day di una mission EGI-DOC su quei repo. Sicurezza
    # Proattiva: non creare il footgun (audit M-222 P2).
}

CODE_EXT = {
    ".php", ".ts", ".tsx", ".js", ".jsx",
    ".py", ".pyw",
    ".css", ".scss", ".less", ".sass",
    ".html", ".vue", ".svelte",
    ".sh", ".bash", ".zsh",
    ".sql",
    ".yaml", ".yml", ".toml",
    ".xml",
    ".env", ".env.example",
    ".gitignore", ".editorconfig",
}

DOC_EXT = {".md", ".txt", ".rst"}

ALWAYS_SKIP = re.compile(
    r'(^|/)(node_modules|vendor|\.next|dist|build|__pycache__|\.git)/'
    r'|_archive/'
)


def classify_file(fname):
    """Return 'code', 'doc', or None (skip)."""
    if ALWAYS_SKIP.search(fname):
        return None
    lower = fname.lower()
    if lower.endswith(".blade.php"):
        return "code"
    _, ext = os.path.splitext(lower)
    if ext in CODE_EXT:
        return "code"
    if ext in DOC_EXT:
        return "doc"
    return None

TAG_WEIGHTS = {
    "FEAT": 1.0, "FIX": 1.5, "REFACTOR": 2.0, "TEST": 1.2, "DEBUG": 1.3,
    "DOC": 0.8, "CONFIG": 0.7, "CHORE": 0.6, "I18N": 0.7, "PERF": 1.4,
    "SECURITY": 1.8, "WIP": 0.3, "REVERT": 0.5, "MERGE": 0.4, "DEPLOY": 0.8,
    "UPDATE": 0.6, "UNTAGGED": 0.5, "ARCH": 1.6, "DEBITO": 0.7,
}


def get_connection():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASS,
    )


def parse_tag(message):
    import re
    m = re.match(r"^\[([A-Z_-]+)\]", message)
    if m:
        return m.group(1)
    m = re.match(r"^(feat|fix|refactor|test|docs|chore|perf|ci|build)[\(:]", message, re.I)
    if m:
        t = m.group(1).upper()
        return "DOC" if t == "DOCS" else t
    if message.startswith("Merge "):
        return "MERGE"
    return "UNTAGGED"


def collect_target_cells(registry_path):
    """Return set of (repo_name, date_str) touched by any mission's by_repo_day,
    plus the overall date range per repo for efficient git log invocations."""
    with open(registry_path) as f:
        registry = json.load(f)

    cells = set()
    repo_bounds = {}
    for m in registry.get("missions", []):
        if m.get("stato") != "completed":
            continue
        stats = m.get("stats") or {}
        for entry in stats.get("by_repo_day", []):
            repo = entry.get("repo")
            date = entry.get("date")
            if not repo or not date:
                continue
            cells.add((repo, date))
            lo, hi = repo_bounds.get(repo, (date, date))
            if date < lo:
                lo = date
            if date > hi:
                hi = date
            repo_bounds[repo] = (lo, hi)
    return cells, repo_bounds


def scan_repo_day_totals(repo_dir, since_str, until_str, repo_name=""):
    """Run `git log --all --numstat` across the date range and return
    {date_str: {'commits': set, 'added': int, 'deleted': int,
               'files': set, 'tags': {tag: count}}}.
    Counts ALL commits and ALL file changes — raw git reality."""
    try:
        d_since = datetime.strptime(since_str, "%Y-%m-%d") - timedelta(days=1)
        d_until = datetime.strptime(until_str, "%Y-%m-%d") + timedelta(days=1)
    except Exception:
        return {}

    cmd = [
        "git", "-C", repo_dir, "log", "--all",
        f"--since={d_since.strftime('%Y-%m-%d')}",
        f"--until={d_until.strftime('%Y-%m-%d')} 23:59:59",
        "--pretty=format:COMMIT|%H|%ad|%s",
        "--date=short",
        "--numstat",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        log_output = result.stdout.strip()
    except Exception:
        return {}

    by_day = {}
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
                slot = by_day.setdefault(current_date, {
                    "commits": set(), "added": 0, "deleted": 0,
                    "files": set(), "tags": {},
                })
                if current_hash not in slot["commits"]:
                    slot["commits"].add(current_hash)
                    tag = parse_tag(msg)
                    slot["tags"][tag] = slot["tags"].get(tag, 0) + 1
            continue
        parts = line.split("\t")
        if len(parts) >= 3 and current_hash and current_date:
            fname = parts[2]
            if classify_file(fname) is None:
                continue
            added = int(parts[0]) if parts[0].isdigit() else 0
            deleted = int(parts[1]) if parts[1].isdigit() else 0
            slot = by_day.get(current_date)
            if slot is not None:
                slot["added"] += added
                slot["deleted"] += deleted
                if fname:
                    slot["files"].add(fname)
    return by_day


def classify_day_type(tag_counts, total):
    if total == 0:
        return ("MIXED", "📦", 1.0)
    dominant = max(tag_counts, key=tag_counts.get)
    share = tag_counts[dominant] / total
    if share < 0.5:
        return ("MIXED", "📦", 1.0)
    mapping = {
        "FEAT": ("FEATURE_DEV", "✨", 1.0),
        "FIX": ("BUG_FIXING", "🐞", 1.3),
        "REFACTOR": ("REFACTORING", "🛠️", 1.5),
        "DOC": ("DOCS", "📝", 0.8),
        "CONFIG": ("CONFIG", "⚙️", 0.7),
        "TEST": ("TESTING", "🧪", 1.2),
        "CHORE": ("CHORE", "🧹", 0.6),
        "I18N": ("I18N", "🌐", 0.7),
        "PERF": ("PERF", "⚡", 1.4),
        "SECURITY": ("SECURITY", "🔒", 1.8),
        "DEPLOY": ("DEPLOY", "🚀", 0.8),
        "ARCH": ("ARCHITECTURE", "🏛️", 1.6),
    }
    return mapping.get(dominant, ("MIXED", "📦", 1.0))


def compute_productivity(total_commits, weighted, lines_net, lines_touched, files, cl_multiplier):
    if total_commits == 0:
        return 0.0, 1.0
    li = math.log(lines_touched + 1)
    fm = math.log(files + 1)
    dp = math.log(total_commits + 1)
    cl = max(1.0, min(3.5, 1.0 + (li + fm + dp) / 6.0))
    capped = min(abs(lines_net), 2000)
    base = (weighted * 10.0) + (capped / 10.0)
    pi = (base * cl_multiplier) / cl if cl > 0 else 0
    return round(pi, 2), round(cl, 2)


def write_daily_stats(conn, cells_by_repo):
    """cells_by_repo: {repo_name: {date_str: slot_dict}}"""
    cur = conn.cursor()
    written = 0
    for repo_name, by_day in cells_by_repo.items():
        for date_str, slot in by_day.items():
            total_commits = len(slot["commits"])
            if total_commits == 0 and slot["added"] == 0 and slot["deleted"] == 0:
                continue
            added = slot["added"]
            deleted = slot["deleted"]
            net = added - deleted
            touched = added + deleted
            files_count = len(slot["files"])
            tag_counts = slot["tags"]
            weighted = sum(c * TAG_WEIGHTS.get(t, 0.5) for t, c in tag_counts.items())
            day_type, icon, multiplier = classify_day_type(tag_counts, total_commits)
            pi, cl = compute_productivity(total_commits, weighted, net, touched, files_count, multiplier)
            coding_hours = max(0.5, round(total_commits * 22 / 60, 2))

            cur.execute(
                f"""
                INSERT INTO {DB_SCHEMA}.daily_stats
                    (date, repo_name, total_commits, weighted_commits,
                     lines_added, lines_deleted, net_lines,
                     productivity_score, files_touched,
                     day_type, day_type_icon, cognitive_load,
                     coding_hours, testing_hours, tags_breakdown)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (date, repo_name) DO UPDATE SET
                    total_commits    = EXCLUDED.total_commits,
                    weighted_commits = EXCLUDED.weighted_commits,
                    lines_added      = EXCLUDED.lines_added,
                    lines_deleted    = EXCLUDED.lines_deleted,
                    net_lines        = EXCLUDED.net_lines,
                    productivity_score = EXCLUDED.productivity_score,
                    files_touched    = EXCLUDED.files_touched,
                    day_type         = EXCLUDED.day_type,
                    day_type_icon    = EXCLUDED.day_type_icon,
                    cognitive_load   = EXCLUDED.cognitive_load,
                    coding_hours     = EXCLUDED.coding_hours,
                    testing_hours    = EXCLUDED.testing_hours,
                    tags_breakdown   = EXCLUDED.tags_breakdown
                """,
                (
                    date_str, repo_name, total_commits, round(weighted, 2),
                    added, deleted, net,
                    pi, files_count,
                    day_type, icon, cl,
                    coding_hours, coding_hours, Json(tag_counts),
                ),
            )
            written += 1
    conn.commit()
    return written


def rebuild_weekly_stats(conn, affected_weeks):
    cur = conn.cursor()
    updated = 0
    for (year, week) in sorted(affected_weeks):
        cur.execute(
            f"""
            INSERT INTO {DB_SCHEMA}.weekly_stats (year, week, repo_name, productivity_score, metrics)
            SELECT
                EXTRACT(ISOYEAR FROM date)::int AS year,
                EXTRACT(WEEK FROM date)::int AS week,
                repo_name,
                SUM(productivity_score) AS productivity_score,
                jsonb_build_object(
                    'weighted_commits', SUM(weighted_commits),
                    'lines_touched',    SUM(lines_added + lines_deleted),
                    'total_commits',    SUM(total_commits)
                ) AS metrics
            FROM {DB_SCHEMA}.daily_stats
            WHERE EXTRACT(ISOYEAR FROM date) = %s
              AND EXTRACT(WEEK FROM date) = %s
            GROUP BY year, week, repo_name
            ON CONFLICT (year, week, repo_name) DO UPDATE SET
                productivity_score = EXCLUDED.productivity_score,
                metrics            = EXCLUDED.metrics
            """,
            (year, week),
        )
        updated += cur.rowcount
    conn.commit()
    return updated


MISSION_TYPE_MULTIPLIER = {
    "feature": 1.0, "bugfix": 1.3, "refactor": 1.5,
    "docsync": 0.8, "audit": 1.1, "lso-evolution": 1.5, "strutturale": 1.3,
}


def _upsert_mission_row(cur, organ, nm):
    """Scrive una riga mission_stats canonica (PK organ, mission_id). nm =
    output di ecosystem.normalize_mission. Git-stats ricche solo dove l'organo
    è già enrichato (EGI-DOC); altrove 0 finché non gira l'enrich per-organo."""
    stats = nm["stats"]
    repos = list({e["repo"] for e in stats.get("by_repo_day", [])})
    mtype = nm["mission_type"]
    type_weight = MISSION_TYPE_MULTIPLIER.get(mtype, 1.0)
    files_mod = nm["files_modified"]

    d_open, d_close = nm["date_opened"], nm["date_closed"]
    duration = 1
    if d_open and d_close and d_close != "pending":
        try:
            dt_open = datetime.strptime(d_open[:10], "%Y-%m-%d")
            dt_close = datetime.strptime(d_close[:10], "%Y-%m-%d")
            duration = max(1, (dt_close - dt_open).days + 1)
        except Exception:
            pass

    cur.execute(f"""
        INSERT INTO {DB_SCHEMA}.mission_stats
            (organ, mission_id, title, date_opened, date_closed, status,
             mission_type, organs, repos, cross_organ,
             files_modified, files_count, files_created,
             doc_sync_executed, duration_days, type_weight,
             total_commits, weighted_commits,
             lines_added, lines_deleted, lines_net, lines_touched,
             cognitive_load, productivity_index, tags_breakdown,
             ingested_at)
        VALUES (%s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s,
                CURRENT_TIMESTAMP)
        ON CONFLICT (organ, mission_id) DO UPDATE SET
            title = EXCLUDED.title,
            date_opened = EXCLUDED.date_opened,
            date_closed = EXCLUDED.date_closed,
            status = EXCLUDED.status,
            mission_type = EXCLUDED.mission_type,
            organs = EXCLUDED.organs,
            repos = EXCLUDED.repos,
            cross_organ = EXCLUDED.cross_organ,
            files_modified = EXCLUDED.files_modified,
            files_count = EXCLUDED.files_count,
            doc_sync_executed = EXCLUDED.doc_sync_executed,
            duration_days = EXCLUDED.duration_days,
            type_weight = EXCLUDED.type_weight,
            total_commits = EXCLUDED.total_commits,
            weighted_commits = EXCLUDED.weighted_commits,
            lines_added = EXCLUDED.lines_added,
            lines_deleted = EXCLUDED.lines_deleted,
            lines_net = EXCLUDED.lines_net,
            lines_touched = EXCLUDED.lines_touched,
            cognitive_load = EXCLUDED.cognitive_load,
            productivity_index = EXCLUDED.productivity_index,
            tags_breakdown = EXCLUDED.tags_breakdown,
            ingested_at = CURRENT_TIMESTAMP
    """, (
        organ, nm["id"], nm["title"], d_open, d_close, nm["status"],
        mtype, Json(nm["organs"]), Json(repos), nm["cross_organ"],
        Json(files_mod), len(files_mod), 0,
        nm["doc_sync_executed"], duration, type_weight,
        stats.get("total_commits", 0), stats.get("weighted_commits", 0),
        stats.get("lines_added", 0), stats.get("lines_deleted", 0),
        stats.get("lines_net", 0), stats.get("lines_touched", 0),
        stats.get("cognitive_load", 1.0), stats.get("productivity_index", 0),
        Json(stats.get("tags_breakdown", {})),
    ))


def sync_mission_stats(conn, registry_path=None):
    """M-220: sync mission_stats da TUTTI i registry dell'ecosistema (non solo
    EGI-DOC). Ogni riga taggata con l'organo. Normalizza i 2 schemi coesistenti.
    M-221: per le missioni senza git-stats ricche (PI=0), fallback su
    enrich-by-message (commit attribuiti per id-missione, cross-repo).
    registry_path è ignorato (retro-compat firma); la sorgente è la discovery."""
    import enrich_by_message  # lazy: evita import circolare a load
    grep_stats = enrich_by_message.collect_mission_git_stats()

    cur = conn.cursor()
    synced = 0
    per_organ = {}
    for organ, missions in sorted(ecosystem.discover_registries().items()):
        n = 0
        for m in missions:
            nm = ecosystem.normalize_mission(m)
            if nm is None:
                continue
            # fallback M-221: usa grep-by-id SOLO per missioni senza attribuzione
            # ricca (no commit, no by_repo_day). Guard preciso: non sovrascrive
            # mai stats ricche con PI non computato (P0 audit M-221).
            s = nm["stats"]
            has_rich = (s.get("total_commits", 0) or 0) > 0 or bool(s.get("by_repo_day"))
            if not has_rich and nm["id"] in grep_stats:
                nm["stats"] = grep_stats[nm["id"]]
            _upsert_mission_row(cur, organ, nm)
            n += 1
        per_organ[organ] = n
        synced += n
    conn.commit()
    sync_mission_stats.last_per_organ = per_organ
    return synced


def main():
    print(f"{'='*70}")
    print("  Mission Registry → DB v5.1  (reality-only + mission_stats sync)")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  Source: {REGISTRY_PATH}")
    print(f"{'='*70}\n")

    cells, repo_bounds = collect_target_cells(REGISTRY_PATH)
    if not cells:
        print("  No target cells found in registry. Nothing to ingest.")
        return

    print(f"  {len(cells)} (repo, date) cells referenced by missions.")
    print(f"  Scanning {len(repo_bounds)} repos with local git log...\n")

    cells_by_repo = defaultdict(dict)
    missing_repos = []
    for repo_name, (lo, hi) in sorted(repo_bounds.items()):
        local_dir = REPO_TO_DIR.get(repo_name)
        if not local_dir or not Path(local_dir).exists():
            missing_repos.append(repo_name)
            continue
        by_day = scan_repo_day_totals(local_dir, lo, hi, repo_name)
        kept = 0
        for date_str, slot in by_day.items():
            if (repo_name, date_str) in cells:
                cells_by_repo[repo_name][date_str] = slot
                kept += 1
        print(f"  {repo_name:45s}  {lo} → {hi}  ({kept} cells)")

    if missing_repos:
        print("\n  ⚠️  Repos with no local clone (skipped):")
        for r in missing_repos:
            print(f"     - {r}")

    conn = get_connection()
    try:
        ensure_schema(conn)  # M-220: auto-allinea lo schema (organ + PK) prima dell'ingest
        written = write_daily_stats(conn, cells_by_repo)
        print(f"\n  ✓ {written} daily_stats rows upserted (real git numbers)")

        affected_weeks = set()
        for repo_name, by_day in cells_by_repo.items():
            for date_str in by_day.keys():
                iso = datetime.strptime(date_str, "%Y-%m-%d").date().isocalendar()
                affected_weeks.add((iso[0], iso[1]))
        updated = rebuild_weekly_stats(conn, affected_weeks)
        print(f"  ✓ {updated} weekly_stats rows rebuilt")

        synced = sync_mission_stats(conn)
        print(f"  ✓ {synced} mission_stats rows synced from ALL ecosystem registries")
        for organ, n in sorted(getattr(sync_mission_stats, "last_per_organ", {}).items()):
            print(f"       {organ:42s} {n}")
    finally:
        conn.close()

    print("\n  Done.")


if __name__ == "__main__":
    main()
