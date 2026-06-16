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


# M-249: le statistiche sono dati VIVI (auto-refresh dai registry). Senza header
# anti-cache il browser ricicla la risposta vecchia anche al reload → la dashboard
# sembra "rotta/ferma" con dati stale. no-store forza il browser a ri-scaricare
# sempre le metriche correnti. Niente più "hard refresh" manuale.
@app.after_request
def _no_store_api(resp):
    # M-266: /api/public/* è consumato dal sito statico fabiocherici.com —
    # cache breve (60s) per proteggere lo SQLite da fetch ripetuti + CORS
    # ristretto al solo dominio del sito. Il resto di /api/ resta no-store.
    if request.path.startswith("/api/public/"):
        # cache pubblica SOLO su 200 — gli errori non vanno cacheati (audit M-266 R1)
        if resp.status_code == 200:
            resp.headers["Cache-Control"] = "public, max-age=60"
        else:
            resp.headers["Cache-Control"] = "no-store"
        resp.headers["Access-Control-Allow-Origin"] = "https://fabiocherici.com"
        resp.headers["Vary"] = "Origin"
        return resp
    if request.path.startswith("/api/"):
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
    return resp

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

    limit = request.args.get('limit', 1000, type=int)
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

        # Individual missions — `organ` (provenienza/registry) disambigua i
        # mission_id duplicati cross-organo; distinto da `organs` (organi toccati).
        cur.execute(f"""
            SELECT organ, mission_id, title, date_opened, date_closed, status,
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


@app.route('/api/v2/stats/daily', methods=['GET'])
def get_v2_daily():
    """Daily stats from SQLite serving (fonte unica) — v2.0 metrics."""
    from stats_v2 import aggregate_daily
    try:
        data = aggregate_daily()
        limit = request.args.get('limit', 90, type=int)
        return jsonify(data[-limit:])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/v2/stats/weekly', methods=['GET'])
def get_v2_weekly():
    """Weekly stats from SQLite serving (fonte unica) — v2.0 metrics."""
    from stats_v2 import aggregate_daily, aggregate_weekly
    try:
        daily = aggregate_daily()
        data = aggregate_weekly(daily)
        limit = request.args.get('limit', 1000, type=int)
        return jsonify(data[-limit:])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/v2/stats/monthly', methods=['GET'])
def get_v2_monthly():
    """Monthly stats from SQLite serving (fonte unica) — v2.0 metrics."""
    from stats_v2 import aggregate_daily, aggregate_monthly
    try:
        daily = aggregate_daily()
        data = aggregate_monthly(daily)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/v2/stats/missions_by_day', methods=['GET'])
def get_v2_missions_by_day():
    """M-245: mission chiuse giorno-per-giorno suddivise per organo (tutti gli
    organi multi-registry). Alimenta la tabella giorno×organo e il grafico
    giornaliero del frontend."""
    from stats_v2 import daily_missions_by_organ
    try:
        return jsonify(daily_missions_by_organ())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/v2/stats/daily_detail', methods=['GET'])
def get_v2_daily_detail():
    """Daily detail MISSION-ONLY from SQLite serving (fonte unica) — M-229.

    Sostituisce /api/stats/daily_detail (Postgres all-repo) per la dashboard:
    conta SOLO il lavoro-mission (Principio di esclusività mission).
    """
    from stats_v2 import daily_detail
    date_str = request.args.get('date')
    if not date_str:
        return jsonify({"error": "Date parameter required (YYYY-MM-DD)"}), 400
    try:
        return jsonify(daily_detail(date_str))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/v2/stats/missions', methods=['GET'])
def get_v2_missions():
    """All mission metrics with CL v2.0 + PI v2.0."""
    from stats_v2 import completed_missions, compute_mission_metrics
    try:
        missions = completed_missions()
        metrics = [compute_mission_metrics(m) for m in missions]
        tipo = request.args.get('type')
        if tipo:
            metrics = [m for m in metrics if m["tipo"] == tipo]
        return jsonify(metrics)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/v2/stats/missions_open', methods=['GET'])
def get_v2_missions_open():
    """M-FUC-054 (ADDITIVO): mission IN CORSO (WIP) per il cockpit Nexus.

    Espone la tabella additiva missions_open (partizione disgiunta da `missions`):
    NON altera i conteggi prod. Shape: [{mission_id,organ,title,status,
    mission_type,date_opened}]. Stesso pattern try/except degli endpoint v2."""
    from stats_v2 import open_missions
    try:
        return jsonify(open_missions())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/public/site-stats', methods=['GET'])
def get_public_site_stats():
    """Aggregato PUBBLICO per il widget cantiere di fabiocherici.com — M-266.

    SOLO totali (ore, progetti, righe, ultima attività) — mai nomi progetto.
    Esposto senza auth dal vhost (location /api/public/), CORS ristretto a
    fabiocherici.com via after_request, cache 60s.
    """
    from public_stats import site_stats
    try:
        return jsonify(site_stats())
    except Exception as e:
        # Endpoint NON autenticato: mai dettagli interni al client (audit M-266 R1).
        # Dettaglio solo nel log server-side; risposta generica e non cacheabile.
        import sys
        print(f"[public_site_stats] ERROR: {e}", file=sys.stderr)
        resp = jsonify({"error": "stats unavailable"})
        resp.headers["Cache-Control"] = "no-store"
        return resp, 500


@app.route('/api/v2/stats/summary', methods=['GET'])
def get_v2_summary():
    """Overall summary — all-time productivity stats."""
    from stats_v2 import summary_stats
    try:
        return jsonify(summary_stats())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/v2/stats/hours', methods=['GET'])
def get_v2_hours():
    """Ore per progetto (manual + stima-commit) dallo SQLite serving — M-234."""
    from stats_v2 import hours_by_project
    try:
        return jsonify(hours_by_project())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/v2/stats/time_entries', methods=['POST'])
def post_v2_time_entry():
    """Aggiunge una voce ore MANUALE al ledger del progetto — M-237.

    Lato-scrittura dell'asse ORE (M-234 era sola lettura). Payload JSON:
    {project, date(YYYY-MM-DD), minutes(int>0), description}. project DEVE essere
    whitelisted (solo nomi in projects.json -> niente path traversal). Flusso:
    valida -> append ATOMICO al TIME_ENTRIES.json dell'istanza (tmp+os.replace,
    no shell) -> refresh SQLite IN-PROCESS (aggregate(), niente subprocess) cosi
    la voce compare subito in GET /api/v2/stats/hours -> 201. Validazione fallita
    -> 400 SENZA scrittura (UEM-first: errore strutturato, mai 500 su input utente).
    """
    from time_entries_write import validate_payload, append_entry, TimeEntryError
    from aggregate_to_sqlite import aggregate, DEFAULT_DB

    payload = request.get_json(silent=True)
    try:
        project, instance_root, entry = validate_payload(payload)
    except TimeEntryError as exc:
        return jsonify({"error": str(exc)}), 400

    try:
        path = append_entry(instance_root, entry)
        aggregate(DEFAULT_DB)  # refresh serving SQLite (idempotente, full rebuild)
    except TimeEntryError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    return jsonify({
        "ok": True,
        "project": project,
        "entry": entry,
        "path": path,
    }), 201


if __name__ == '__main__':
    import json
    app.run(host='0.0.0.0', debug=True, port=5000)
