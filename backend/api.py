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

if __name__ == '__main__':
    app.run(debug=True, port=5000)
