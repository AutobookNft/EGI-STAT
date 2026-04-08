from flask import Flask, jsonify, request
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import dotenv
from pathlib import Path

# Load env variables
env_path = Path(__file__).parent / '.env'
dotenv.load_dotenv(env_path)

app = Flask(__name__)
CORS(app)

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_DATABASE")
DB_USER = os.getenv("DB_USERNAME")
DB_PASS = os.getenv("DB_PASSWORD")

DB_SCHEMA = os.getenv("DB_SCHEMA", "stat")

def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        return conn
    except Exception as e:
        print(f"❌ DB Connection Error: {e}")
        return None

@app.route('/api/stats/weekly', methods=['GET'])
def get_weekly_stats():
    """
    Returns weekly aggregated stats from PostgreSQL.
    """
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        # Aggregate ALL repositories by (year, week)
        query = f"""
            SELECT
                year,
                week,
                SUM(productivity_score) as productivity_score,
                jsonb_build_object(
                    'weighted_commits', SUM((metrics->>'weighted_commits')::float),
                    'lines_touched', SUM((metrics->>'lines_touched')::int),
                    'total_commits', SUM((metrics->>'total_commits')::int)
                ) as metrics
            FROM {DB_SCHEMA}.weekly_stats
            GROUP BY year, week
            ORDER BY year DESC, week DESC
            LIMIT 50
        """
        cur.execute(query)
        rows = cur.fetchall()
        
        cur.close()
        conn.close()
        return jsonify(rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/stats/daily_detail', methods=['GET'])
def get_daily_detail():
    """
    Returns detailed daily stats for a specific date (YYYY-MM-DD).
    Aggregates metrics across all repositories.
    """
    date_str = request.args.get('date')
    if not date_str:
        return jsonify({"error": "Date parameter required (YYYY-MM-DD)"}), 400
        
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
        
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # 1. Get Per-Repo Details
        cur.execute(f"""
            SELECT 
                repo_name,
                total_commits,
                weighted_commits,
                lines_added, lines_deleted, net_lines, files_touched,
                productivity_score,
                day_type, day_type_icon, cognitive_load,
                coding_hours, testing_hours
            FROM {DB_SCHEMA}.daily_stats
            WHERE date = %s
            ORDER BY productivity_score DESC
        """, (date_str,))
        
        repos = cur.fetchall()
        
        # 2. Aggregation Logic
        summary = {
            "total_commits": 0,
            "weighted_commits": 0.0,
            "lines_added": 0,
            "lines_deleted": 0,
            "net_lines": 0,
            "files_touched": 0,
            "productivity_score": 0.0,
            "coding_hours": 0.0,
            "testing_hours": 0.0,
            "cognitive_load": 0.0,
            "day_type": "MIXED",
            "day_type_icon": "📦"
        }
        
        if repos:
            # Sums — righe e score esclusi per repo doc
            summary["total_commits"] = sum(r["total_commits"] for r in repos)
            summary["weighted_commits"] = sum(r["weighted_commits"] for r in repos)
            summary["lines_added"] = sum(r["lines_added"] for r in repos)
            summary["lines_deleted"] = sum(r["lines_deleted"] for r in repos)
            summary["net_lines"] = sum(r["net_lines"] for r in repos)
            summary["files_touched"] = sum(r["files_touched"] for r in repos)
            summary["productivity_score"] = sum(r["productivity_score"] for r in repos)
            summary["coding_hours"] = sum(r["coding_hours"] or 0 for r in repos)
            summary["testing_hours"] = sum(r["testing_hours"] or 0 for r in repos)
            
            # Averages (Weighted by commits? Or simple avg? Let's use simple avg for load)
            summary["cognitive_load"] = sum(r["cognitive_load"] for r in repos) / len(repos)
            
            # Dominant Day Type
            from collections import Counter
            type_counts = Counter(r["day_type"] for r in repos if r["day_type"])
            if type_counts:
                dominant = type_counts.most_common(1)[0][0]
                summary["day_type"] = dominant
                # Find icon for dominant
                for r in repos:
                    if r["day_type"] == dominant:
                        summary["day_type_icon"] = r["day_type_icon"]
                        break
        
        cur.close()
        conn.close()
        
        return jsonify({
            "date": date_str,
            "summary": summary,
            "repositories": repos
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route('/api/raw_commits', methods=['GET'])
def get_raw_commits():
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
        
    limit = request.args.get('limit', 100)
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        query = f"SELECT * FROM {DB_SCHEMA}.commits ORDER BY date DESC LIMIT %s"
        cur.execute(query, (limit,))
        commits = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(commits)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/stats/missions', methods=['GET'])
def get_mission_stats():
    """
    Returns mission-based statistics.
    Optional params: ?limit=50&type=feature&organ=EGI
    """
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    limit = request.args.get('limit', 50, type=int)
    mission_type = request.args.get('type')
    organ = request.args.get('organ')

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        where_clauses = []
        params = []

        if mission_type:
            where_clauses.append("mission_type = %s")
            params.append(mission_type)
        if organ:
            where_clauses.append("organs @> %s::jsonb")
            params.append(json.dumps([organ]))

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        # Individual missions
        cur.execute(f"""
            SELECT mission_id, title, date_opened, date_closed, status,
                   mission_type, organs, repos, cross_organ,
                   files_count, files_created, doc_sync_executed,
                   duration_days, type_weight
            FROM {DB_SCHEMA}.mission_stats
            {where_sql}
            ORDER BY date_closed DESC NULLS LAST
            LIMIT %s
        """, params + [limit])
        missions = cur.fetchall()

        # Summary aggregation
        cur.execute(f"""
            SELECT
                COUNT(*) as total_missions,
                COUNT(CASE WHEN mission_type = 'feature' THEN 1 END) as features,
                COUNT(CASE WHEN mission_type = 'bugfix' THEN 1 END) as bugfixes,
                COUNT(CASE WHEN mission_type = 'refactor' THEN 1 END) as refactors,
                COUNT(CASE WHEN mission_type = 'docsync' THEN 1 END) as docsyncs,
                COUNT(CASE WHEN mission_type = 'audit' THEN 1 END) as audits,
                COUNT(CASE WHEN mission_type = 'lso-evolution' THEN 1 END) as lso_evolutions,
                COUNT(CASE WHEN cross_organ THEN 1 END) as cross_organ_count,
                COUNT(CASE WHEN doc_sync_executed THEN 1 END) as doc_sync_done,
                AVG(duration_days) as avg_duration,
                SUM(files_count) as total_files_touched,
                AVG(type_weight) as avg_complexity
            FROM {DB_SCHEMA}.mission_stats
            {where_sql}
        """, params)
        summary = cur.fetchone()

        cur.close()
        conn.close()

        return jsonify({
            "missions": missions,
            "summary": summary
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/stats/mission_timeline', methods=['GET'])
def get_mission_timeline():
    """
    Returns missions grouped by week for timeline visualization.
    """
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(f"""
            SELECT
                EXTRACT(ISOYEAR FROM date_closed)::int as year,
                EXTRACT(WEEK FROM date_closed)::int as week,
                COUNT(*) as mission_count,
                array_agg(DISTINCT mission_type) as types,
                SUM(files_count) as files_touched,
                COUNT(CASE WHEN doc_sync_executed THEN 1 END) as doc_sync_count,
                COUNT(CASE WHEN cross_organ THEN 1 END) as cross_organ_count,
                AVG(type_weight) as avg_weight
            FROM {DB_SCHEMA}.mission_stats
            WHERE date_closed IS NOT NULL
            GROUP BY year, week
            ORDER BY year DESC, week DESC
            LIMIT 50
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    import json
    app.run(host='0.0.0.0', debug=True, port=5000)
