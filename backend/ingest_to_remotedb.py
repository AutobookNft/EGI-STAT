import os
import sys
import argparse
from datetime import datetime, timedelta
import math
from collections import Counter
import psycopg2
from psycopg2.extras import Json
import dotenv
from pathlib import Path

# Add core to path
sys.path.append(str(Path(__file__).parent / "core"))

# Import core logic
from core.github_client import GitHubMultiRepoClient, CommitData
from core.tag_system_v2 import TagSystem, DAY_TYPES

# Re-implementing helper functions to ensure stability in ingestion script
# (Avoiding circular dependencies or complex class initializations from full report script)

def classify_day_type(tag_percentages):
    """Classify day based on tag distribution."""
    for day_type, config in DAY_TYPES.items():
        if config['criteria'](tag_percentages):
            return day_type, config['icon'], config['multiplier']
    # Fallback to MIXED
    mixed = DAY_TYPES['MIXED']
    return 'MIXED', mixed['icon'], mixed['multiplier']

def calculate_cognitive_load(commits, files, lines_touched):
    """Calculate cognitive load using log-scaled formula."""
    if commits == 0:
        return 1.0
    
    li = math.log(lines_touched + 1)
    fm = math.log(files + 1)
    dp = math.log(commits + 1)
    
    cl = (li + fm + dp) / 3.0
    cl_normalized = 1.0 + (cl / 2.0)
    return max(1.0, min(3.5, cl_normalized))

def calculate_productivity_index(commits_weighted, lines_net, cognitive_load, day_type_multiplier):
    """Calculate productivity index."""
    if cognitive_load == 0:
        cognitive_load = 1.0

    # Cap lines contribution: beyond 2000 net lines/day is bulk/asset, not productive code
    capped_lines = min(abs(lines_net), 2000)
    base_score = (commits_weighted * 10.0) + (capped_lines / 10.0)
    return (base_score * day_type_multiplier) / cognitive_load

# Load env
dotenv.load_dotenv(Path(__file__).parent / '.env')

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_DATABASE")
DB_USER = os.getenv("DB_USERNAME")
DB_PASS = os.getenv("DB_PASSWORD")
DB_SCHEMA = os.getenv("DB_SCHEMA", "stat")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASS
    )

def ingest_data(days_back=30, target_repo=None):
    if not GITHUB_TOKEN:
        print("❌ GITHUB_TOKEN missing in .env")
        return

    print(f"🚀 Starting Ingestion (Last {days_back} days)...")
    
    # 1. Setup Client
    # All organ repositories in florenceegi org (EGI-STAT excluded — internal tool, not an organ)
    all_repos = [
        "florenceegi/EGI",
        "florenceegi/EGI-HUB",
        "florenceegi/EGI-HUB-HOME-REACT",
        "florenceegi/EGI-INFO",
        "florenceegi/NATAN_LOC",
        "florenceegi/EGI-DOC",
        "florenceegi/egi-credential",
        "florenceegi/EGI-SIGILLO",
        "florenceegi/oracode",
        "florenceegi/la-bottega",
    ]
    
    if target_repo:
        if target_repo not in all_repos:
            print(f"⚠️ Warning: {target_repo} not in standard list, but proceeding...")
        repo_list = [target_repo]
    else:
        repo_list = all_repos 
    
    # Process one repo at a time to show progress
    for repo_name in repo_list:
        print(f"\n🚀 Processing {repo_name}...")
        
        # Instantiate client just for this repo context
        client = GitHubMultiRepoClient(token=GITHUB_TOKEN, repositories=[repo_name])
        tag_sys = TagSystem()

        # 2. Fetch Commits
        since_date = datetime.now() - timedelta(days=days_back)
        try:
            commits = client.get_commits(since=since_date, until=datetime.now())
        except Exception as e:
            print(f"❌ Error fetching {repo_name}: {e}")
            continue
            
        print(f"📥 Fetched {len(commits)} commits for {repo_name}")
        if not commits:
            continue

        # 3. Insert into DB (Per Repo Batch)
        try:
            conn = get_db_connection()
            conn.autocommit = True
            cur = conn.cursor()
            
            # Set search path
            cur.execute(f"SET search_path TO {DB_SCHEMA}, public")
            
            # Data Structures for Aggregation
            daily_commits_map = {} # (date, repo) -> list[commits]
            weekly_commits_map = {} # (year, week, repo) -> list[commits]

            for c in commits:
                # A. Analysis per commit
                tag_name, confidence = tag_sys.parse_tag(c.message)
                
                tags_list = []
                base_weight = 0.5 
                canonic_tag = "UNTAGGED"
                
                if tag_name:
                    config = tag_sys.get_config(tag_name)
                    if config:
                        tags_list.append(config.name)
                        base_weight = config.weight
                        canonic_tag = config.name
                
                # Simplified analysis for Raw Commit storage (legacy compatibility)
                c_analysis = {
                    "tags": tags_list,
                    "weight": base_weight,
                    "net_lines": c.total_changes,
                    "canonic_tag": canonic_tag
                }

                # Save to DB (Raw Commit)
                cur.execute("""
                    INSERT INTO commits (hash, repo_name, author, date, message, stats, tags, analysis)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (hash) DO UPDATE SET analysis = EXCLUDED.analysis
                """, (
                    c.sha, c.repository, c.author, c.date, c.message, 
                    Json({'additions': c.additions, 'deletions': c.deletions, 'total': c.total_changes}), 
                    Json(c_analysis['tags']), Json(c_analysis)
                ))
                
                # B. Group for Aggregation
                dt_obj = c.date.date()
                year, week, _ = dt_obj.isocalendar()
                repo = c.repository
                
                # Daily Group
                key_d = (dt_obj, repo)
                if key_d not in daily_commits_map:
                    daily_commits_map[key_d] = []
                daily_commits_map[key_d].append({
                    "commit": c,
                    "weight": base_weight,
                    "tag": canonic_tag
                })
                
                # Weekly Group
                key_w = (year, week, repo)
                if key_w not in weekly_commits_map:
                    weekly_commits_map[key_w] = []
                weekly_commits_map[key_w].append({
                    "commit": c,
                    "weight": base_weight
                })

            # 4. Insert Daily Stats (Advanced v7 Logic)
            print(f"📊 {repo_name}: Updating Daily Stats...")
            for (d, r), items in daily_commits_map.items():
                # Aggregate metrics
                total_commits = len(items)
                weighted_commits = sum(i["weight"] for i in items)
                
                lines_added = sum(i["commit"].additions for i in items)
                lines_deleted = sum(i["commit"].deletions for i in items)
                lines_touched = lines_added + lines_deleted
                lines_net = lines_added - lines_deleted # Proper net for DB
                
                files_touched_set = set()
                for i in items:
                    files_touched_set.update(i["commit"].files_changed)
                files_touched_count = len(files_touched_set)
                
                # Tag Breakdown
                tag_counts = Counter(i["tag"] for i in items)
                tag_percentages = {tag: (count / total_commits) * 100 for tag, count in tag_counts.items()}
                
                # Classify
                day_type, day_type_icon, type_multiplier = classify_day_type(tag_percentages)
                
                # Calculate Scores
                cognitive_load = calculate_cognitive_load(total_commits, files_touched_count, lines_touched)
                pi_score = calculate_productivity_index(weighted_commits, lines_net, cognitive_load, type_multiplier)
                
                # Time Estimates
                coding_mins = total_commits * 22
                testing_mins = total_commits * 22 # Placeholder logic from v7 script
                
                # Insert Full Data
                cur.execute("""
                    INSERT INTO daily_stats (
                        date, repo_name, 
                        total_commits, weighted_commits, 
                        lines_added, lines_deleted, net_lines, 
                        productivity_score,
                        files_touched, day_type, day_type_icon, cognitive_load,
                        coding_hours, testing_hours, tags_breakdown
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (date, repo_name) DO UPDATE 
                    SET total_commits = EXCLUDED.total_commits,
                        weighted_commits = EXCLUDED.weighted_commits,
                        lines_added = EXCLUDED.lines_added,
                        lines_deleted = EXCLUDED.lines_deleted,
                        net_lines = EXCLUDED.net_lines,
                        productivity_score = EXCLUDED.productivity_score,
                        files_touched = EXCLUDED.files_touched,
                        day_type = EXCLUDED.day_type,
                        day_type_icon = EXCLUDED.day_type_icon,
                        cognitive_load = EXCLUDED.cognitive_load,
                        coding_hours = EXCLUDED.coding_hours,
                        testing_hours = EXCLUDED.testing_hours,
                        tags_breakdown = EXCLUDED.tags_breakdown
                """, (
                    d, r, 
                    total_commits, weighted_commits,
                    lines_added, lines_deleted, lines_net,
                    pi_score,
                    files_touched_count, day_type, day_type_icon, cognitive_load,
                    coding_mins / 60.0, testing_mins / 60.0, Json(tag_counts)
                ))

            # 5. Insert Weekly Stats — aggregate daily PI scores
            print(f"📊 {repo_name}: Updating Weekly Stats...")
            # Build weekly PI by summing daily PIs for this repo
            weekly_pi_from_daily = {}  # (year, week, repo) -> sum of daily PI
            for (d, r2), items in daily_commits_map.items():
                year, week, _ = d.isocalendar()
                key = (year, week, r2)
                if key not in weekly_pi_from_daily:
                    weekly_pi_from_daily[key] = 0.0
                # Re-compute daily PI (same formula as above)
                tc = len(items)
                wc = sum(i["weight"] for i in items)
                la = sum(i["commit"].additions for i in items)
                ld = sum(i["commit"].deletions for i in items)
                lt = la + ld
                ln = la - ld
                fs = set()
                for i in items:
                    fs.update(i["commit"].files_changed)
                tpc = Counter(i["tag"] for i in items)
                tpp = {tag: (count / tc) * 100 for tag, count in tpc.items()}
                _, _, tm = classify_day_type(tpp)
                cl = calculate_cognitive_load(tc, len(fs), lt)
                weekly_pi_from_daily[key] += calculate_productivity_index(wc, ln, cl, tm)

            for (y, w, r), items in weekly_commits_map.items():
                total_commits = len(items)
                weighted_commits = sum(i["weight"] for i in items)
                # Cap per-commit lines to avoid bulk/asset distortion
                lines_touched = sum(min(i["commit"].additions + i["commit"].deletions, 2000) for i in items)

                # Use sum of daily PIs (accurate) instead of raw formula
                pi_score = round(weekly_pi_from_daily.get((y, w, r), 0.0), 1)

                cur.execute("""
                    INSERT INTO weekly_stats (year, week, repo_name, productivity_score, metrics)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (year, week, repo_name) DO UPDATE
                    SET productivity_score = EXCLUDED.productivity_score,
                        metrics = EXCLUDED.metrics
                """, (
                    y, w, r,
                    pi_score,
                    Json({
                        "weighted_commits": round(weighted_commits, 1),
                        "lines_touched": lines_touched,
                        "total_commits": total_commits
                    })
                ))
                
            cur.close()
            conn.close()
            print(f"✅ {repo_name}: Done.")
            
        except Exception as e:
            print(f"❌ Error processing DB for {repo_name}: {e}")
            import traceback
            traceback.print_exc()

    print("\n✅ All Ingestion Complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Ingest Commit Data to Remote DB')
    parser.add_argument('--days', type=int, default=30, help='Days back to scan (default: 30)')
    parser.add_argument('--repo', type=str, help='Specific repo to ingest (optional)')
    args = parser.parse_args()
    
    ingest_data(days_back=args.days, target_repo=args.repo)
