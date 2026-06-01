"""
Rebuild ALL daily_stats cells — WHITELIST approach.

Only counts files with known code/doc extensions.
Everything else is ignored (zero false positives, zero surprises).

Splits lines into code vs documentation for separate tracking.

@author Padmin D. Curtis (AI Partner OS3.0) for Fabio Cherici
@version 2.0.0 (FlorenceEGI — EGI-STAT)
@date 2026-05-09
@purpose Rebuild daily_stats with whitelist-only counting + code/doc split
"""
import os, re, subprocess
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import dotenv
import psycopg2
from psycopg2.extras import Json

dotenv.load_dotenv(Path(__file__).parent / ".env")

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"), port=os.getenv("DB_PORT"),
    dbname=os.getenv("DB_DATABASE"), user=os.getenv("DB_USERNAME"),
    password=os.getenv("DB_PASSWORD"),
)
schema = os.getenv("DB_SCHEMA", "stat")
cur = conn.cursor()

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
    "UPDATE": 0.6, "UNTAGGED": 0.5, "ARCH": 1.6, "DEBITO": 0.7, "MISSION": 1.2,
}

REPO_TO_DIR = {
    "florenceegi/EGI": "/home/fabio/EGI",
    "florenceegi/EGI-HUB": "/home/fabio/EGI-HUB",
    "florenceegi/EGI-HUB-HOME-REACT": "/home/fabio/EGI-HUB-HOME-REACT",
    "florenceegi/EGI-SIGILLO": "/home/fabio/EGI-SIGILLO",
    "florenceegi/egi-credential": "/home/fabio/EGI-Credential",
    "florenceegi/NATAN_LOC": "/home/fabio/NATAN_LOC",
    "florenceegi/EGI-INFO": "/home/fabio/EGI-INFO",
    "florenceegi/EGI-DOC": "/home/fabio/EGI-DOC",
    "florenceegi/EGI-STAT": "/home/fabio/EGI-STAT",
    "florenceegi/oracode": "/home/fabio/oracode",
    "florenceegi/YURI-BIAGINI": "/home/fabio/YURI-BIAGINI",
    "florenceegi/la-bottega": "/home/fabio/LA-BOTTEGA",
    "florenceegi/fabiocherici": "/home/fabio/FABIO-CHERICI-SITE",
    "florenceegi/creator-staging": "/home/fabio/CREATOR-STAGING",
    "florenceegi/gialloro-firenze": "/home/fabio/GIALLORO-FIRENZE",
    "florenceegi/gialloro-firenze-cms": "/home/fabio/GIALLORO-FIRENZE-CMS",
    # DEBITO M-222: NON aggiungere pinocapasso / le-vespe-cafe / os3-matrix qui.
    # Questo script ricostruisce daily_stats da git LOCALE; i loro cloni sono
    # stale (es. 2026-06-01: locale 0 commit vs GitHub 16/37/111) → li
    # sovrascriverebbe azzerandoli. I loro daily vivono in daily_stats via
    # ingest_to_remotedb (GitHub). Questi repo sono "GitHub-only-no-local".
    # Debito strutturale: 3 liste repo (qui + ingest_to_remotedb.all_repos +
    # ingest_missions.REPO_TO_DIR) andrebbero unificate in repos_config.py.
}


def parse_tag(msg):
    m = re.match(r'^\[([A-Z_-]+)\]', msg)
    if m:
        return m.group(1)
    m = re.match(r'^(feat|fix|refactor|test|docs|chore|perf|ci|build)[\(:]', msg, re.I)
    if m:
        t = m.group(1).upper()
        return "DOC" if t == "DOCS" else t
    if msg.startswith("Merge "):
        return "MERGE"
    return "UNTAGGED"


cur.execute(f"SELECT DISTINCT repo_name, date FROM {schema}.daily_stats")
all_cells = [(r[0], str(r[1])) for r in cur.fetchall()]
print(f"Total cells to rebuild: {len(all_cells)}")

repo_dates = defaultdict(set)
for repo, date in all_cells:
    repo_dates[repo].add(date)

updated = 0
for repo_name in sorted(repo_dates):
    dates = repo_dates[repo_name]
    local_dir = REPO_TO_DIR.get(repo_name)
    if not local_dir or not Path(local_dir).exists():
        print(f"  SKIP {repo_name}")
        continue

    lo, hi = min(dates), max(dates)
    d_since = datetime.strptime(lo, "%Y-%m-%d") - timedelta(days=1)
    d_until = datetime.strptime(hi, "%Y-%m-%d") + timedelta(days=1)

    cmd = [
        "git", "-C", local_dir, "log", "--all",
        f"--since={d_since.strftime('%Y-%m-%d')}",
        f"--until={d_until.strftime('%Y-%m-%d')} 23:59:59",
        "--pretty=format:COMMIT|%H|%ad|%s", "--date=short", "--numstat",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    by_day = {}
    current_hash = current_date = None
    for line in r.stdout.strip().split("\n"):
        if not line:
            continue
        if line.startswith("COMMIT|"):
            parts = line.split("|", 3)
            if len(parts) >= 4:
                current_hash = parts[1].strip()
                current_date = parts[2].strip()
                slot = by_day.setdefault(current_date, {
                    "commits": set(),
                    "code_added": 0, "code_deleted": 0,
                    "doc_added": 0, "doc_deleted": 0,
                    "files": set(), "tags": {},
                })
                if current_hash not in slot["commits"]:
                    slot["commits"].add(current_hash)
                    tag = parse_tag(parts[3])
                    slot["tags"][tag] = slot["tags"].get(tag, 0) + 1
            continue
        parts = line.split("\t")
        if len(parts) >= 3 and current_hash and current_date:
            fname = parts[2]
            kind = classify_file(fname)
            if kind is None:
                continue
            added = int(parts[0]) if parts[0].isdigit() else 0
            deleted = int(parts[1]) if parts[1].isdigit() else 0
            slot = by_day.get(current_date)
            if slot:
                if kind == "code":
                    slot["code_added"] += added
                    slot["code_deleted"] += deleted
                else:
                    slot["doc_added"] += added
                    slot["doc_deleted"] += deleted
                if fname:
                    slot["files"].add(fname)

    for date_str in dates:
        slot = by_day.get(date_str, {
            "commits": set(),
            "code_added": 0, "code_deleted": 0,
            "doc_added": 0, "doc_deleted": 0,
            "files": set(), "tags": {},
        })
        tc = len(slot["commits"])
        ca, cd = slot["code_added"], slot["code_deleted"]
        da, dd = slot["doc_added"], slot["doc_deleted"]
        f = len(slot["files"])
        tags = slot["tags"]
        w = sum(c * TAG_WEIGHTS.get(t, 0.5) for t, c in tags.items())

        cur.execute(f"""UPDATE {schema}.daily_stats
            SET total_commits = %s, weighted_commits = %s,
                lines_added = %s, lines_deleted = %s, net_lines = %s,
                files_touched = %s, tags_breakdown = %s,
                code_added = %s, code_deleted = %s,
                doc_added = %s, doc_deleted = %s
            WHERE repo_name = %s AND date = %s""",
            (tc, round(w, 2), ca, cd, ca - cd,
             f, Json(tags), ca, cd, da, dd, repo_name, date_str))
        updated += 1

    print(f"  {repo_name:<45} {lo} -> {hi} ({len(dates)} cells)")

conn.commit()
print(f"\nUpdated {updated} cells")

# Rebuild weekly with code/doc split in metrics
cur.execute(f"""SELECT DISTINCT EXTRACT(ISOYEAR FROM date)::int, EXTRACT(WEEK FROM date)::int
    FROM {schema}.daily_stats""")
weeks = cur.fetchall()
for year, week in weeks:
    cur.execute(f"""
        INSERT INTO {schema}.weekly_stats (year, week, repo_name, productivity_score, metrics)
        SELECT EXTRACT(ISOYEAR FROM date)::int, EXTRACT(WEEK FROM date)::int, repo_name,
            SUM(productivity_score),
            jsonb_build_object(
                'weighted_commits', SUM(weighted_commits),
                'lines_touched', SUM(lines_added - lines_deleted),
                'total_commits', SUM(total_commits),
                'code_added', SUM(code_added),
                'code_deleted', SUM(code_deleted),
                'doc_added', SUM(doc_added),
                'doc_deleted', SUM(doc_deleted)
            )
        FROM {schema}.daily_stats
        WHERE EXTRACT(ISOYEAR FROM date) = %s AND EXTRACT(WEEK FROM date) = %s
        GROUP BY 1, 2, repo_name
        ON CONFLICT (year, week, repo_name) DO UPDATE SET
            productivity_score = EXCLUDED.productivity_score,
            metrics = EXCLUDED.metrics
    """, (year, week))
conn.commit()
print(f"Weekly stats rebuilt for {len(weeks)} weeks")
conn.close()
print("Done.")
