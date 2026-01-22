import os
import sys
import argparse
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import Json
import dotenv
from pathlib import Path

# Add core to path
sys.path.append(str(Path(__file__).parent / "core"))

# Import core logic
from core.github_client import GitHubMultiRepoClient, CommitData
from core.tag_system_v2 import TagSystem
# We need to reimplement or import the Analyzer logic. 
# For robustness/OS3, I will reimplement the specific calculation here 
# to ensure it strictly matches the DB schema we just created.

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

def calculate_productivity(commit: CommitData, tag_system: TagSystem):
    # Replicating v7 logic ADAPTED for TagSystem v2
    tag_name, confidence = tag_system.parse_tag(commit.message)
    
    tags_list = []
    base_weight = 0.5 # Fallback
    
    if tag_name:
        config = tag_system.get_config(tag_name)
        if config:
            tags_list.append(config.name)
            base_weight = config.weight
            
    # Lines net (abs value for PI)
    net_lines = commit.total_changes # Using total changes
    
    # PI Formula: (Weighted * 10) + (Net / 10)
    pi_score = (base_weight * 10.0) + (net_lines / 10.0)
    
    return {
        "tags": tags_list,
        "weight": base_weight,
        "pi_score": pi_score,
        "net_lines": net_lines
    }

def ingest_data(days_back=30):
    if not GITHUB_TOKEN:
        print("❌ GITHUB_TOKEN missing in .env")
        return

    print(f"🚀 Starting Ingestion (Last {days_back} days)...")
    
    # 1. Setup Client
    # Valid list from config - ALL 6 REPOSITORIES
    repo_list = [
        "AutobookNft/EGI", 
        "AutobookNft/EGI-HUB", 
        "AutobookNft/EGI-HUB-HOME-REACT",
        "AutobookNft/EGI-INFO",
        "AutobookNft/EGI-STAT",
        "AutobookNft/NATAN_LOC"
    ] 
    
    # Process one repo at a time to show progress
    for repo_name in repo_list:
        print(f"\n🚀 Processing {repo_name}...")
        
        # Instantiate client just for this repo context if needed, 
        # but better to use the multi-client to fetch specific repo
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
            
            daily_aggr = {} 
            weekly_aggr = {} 

            for c in commits:
                # A. Insert Raw Commit
                analysis = calculate_productivity(c, tag_sys)
                
                # Save to DB
                cur.execute("""
                    INSERT INTO commits (hash, repo_name, author, date, message, stats, tags, analysis)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (hash) DO UPDATE SET analysis = EXCLUDED.analysis
                """, (
                    c.sha, c.repository, c.author, c.date, c.message, 
                    Json({'additions': c.additions, 'deletions': c.deletions, 'total': c.total_changes}), 
                    Json(analysis['tags']), Json(analysis)
                ))
                
                # B. Aggregate Daily & Weekly
                dt = c.date.date()
                year, week, _ = dt.isocalendar()
                repo = c.repository # Should match repo_name
                
                # Daily Key
                key_d = (dt, repo)
                if key_d not in daily_aggr:
                    daily_aggr[key_d] = {"pi": 0, "weighted": 0, "lines": 0, "count": 0, "added": 0, "deleted": 0, "net": 0}
                    
                daily_aggr[key_d]["pi"] += analysis["pi_score"]
                daily_aggr[key_d]["weighted"] += analysis["weight"]
                daily_aggr[key_d]["lines"] += analysis["net_lines"]
                daily_aggr[key_d]["count"] += 1
                daily_aggr[key_d]["added"] += c.additions
                daily_aggr[key_d]["deleted"] += c.deletions
                daily_aggr[key_d]["net"] += c.total_changes
                
                # Weekly Key
                key_w = (year, week, repo)
                if key_w not in weekly_aggr:
                    weekly_aggr[key_w] = {"pi": 0, "weighted": 0, "lines": 0, "count": 0}
                    
                weekly_aggr[key_w]["pi"] += analysis["pi_score"]
                weekly_aggr[key_w]["weighted"] += analysis["weight"]
                weekly_aggr[key_w]["lines"] += analysis["net_lines"]
                weekly_aggr[key_w]["count"] += 1

            # 4. Insert Aggregations (Per Repo)
            
            # A. Daily Stats
            print(f"📊 {repo_name}: Updating Daily Stats...")
            for (d, r), data in daily_aggr.items():
                cur.execute("""
                    INSERT INTO daily_stats (
                        date, repo_name, total_commits, weighted_commits, 
                        lines_added, lines_deleted, net_lines, productivity_score
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (date, repo_name) DO UPDATE 
                    SET total_commits = EXCLUDED.total_commits,
                        weighted_commits = EXCLUDED.weighted_commits,
                        lines_added = EXCLUDED.lines_added,
                        lines_deleted = EXCLUDED.lines_deleted,
                        net_lines = EXCLUDED.net_lines,
                        productivity_score = EXCLUDED.productivity_score
                """, (
                    d, r, 
                    data["count"], data["weighted"], 
                    data["added"], data["deleted"], data["net"], 
                    data["pi"]
                ))

            # B. Weekly Stats
            print(f"📊 {repo_name}: Updating Weekly Stats...")
            for (y, w, r), data in weekly_aggr.items():
                cur.execute("""
                    INSERT INTO weekly_stats (year, week, repo_name, productivity_score, metrics)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (year, week, repo_name) DO UPDATE 
                    SET productivity_score = EXCLUDED.productivity_score,
                        metrics = EXCLUDED.metrics
                """, (
                    y, w, r, 
                    data["pi"], 
                    Json({
                        "weighted_commits": data["weighted"], 
                        "lines_touched": data["lines"], 
                        "total_commits": data["count"]
                    })
                ))
                
            cur.close()
            conn.close()
            print(f"✅ {repo_name}: Done.")
            
        except Exception as e:
            print(f"❌ Error processing DB for {repo_name}: {e}")

    print("\n✅ All Ingestion Complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Ingest Commit Data to Remote DB')
    parser.add_argument('--days', type=int, default=30, help='Days back to scan (default: 30)')
    args = parser.parse_args()
    
    ingest_data(days_back=args.days)
