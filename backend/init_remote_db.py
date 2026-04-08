import os
import psycopg2
from psycopg2 import sql
import dotenv
from pathlib import Path

# Load config
dotenv.load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_DATABASE")
DB_USER = os.getenv("DB_USERNAME")
DB_PASS = os.getenv("DB_PASSWORD")
DB_SCHEMA = os.getenv("DB_SCHEMA", "stat")

def init_db():
    print(f"🔌 Connecting to {DB_HOST} ({DB_NAME})...")
    
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        conn.autocommit = True
        cur = conn.cursor()
        
        # 1. Create Schema
        print(f"📦 checking/creating schema '{DB_SCHEMA}'...")
        cur.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(DB_SCHEMA)))
        
        # Set search path for this session
        cur.execute(sql.SQL("SET search_path TO {}, public").format(sql.Identifier(DB_SCHEMA)))
        
        # 2. Create Tables
        print("🔨 Creating tables...")
        
        # Table: Commits (Raw Data)
        # Replacing SQLite logic with proper Postgres types (JSONB for metadata)
        cur.execute(sql.SQL("""
            CREATE TABLE IF NOT EXISTS {}.commits (
                hash VARCHAR(40) PRIMARY KEY,
                repo_name VARCHAR(100) NOT NULL,
                author VARCHAR(100),
                email VARCHAR(100),
                date TIMESTAMP WITH TIME ZONE,
                message TEXT,
                branch VARCHAR(100),
                stats JSONB DEFAULT '{{}}'::jsonb,  -- {{added, deleted, net}}
                tags JSONB DEFAULT '[]'::jsonb,    -- List of tags
                analysis JSONB DEFAULT '{{}}'::jsonb, -- {{cognitive_load, productivity_score}}
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """).format(sql.Identifier(DB_SCHEMA)))
        
        # Table: Daily Aggregations (Pre-calculated for fast charts)
        cur.execute(sql.SQL("""
            CREATE TABLE IF NOT EXISTS {}.daily_stats (
                id SERIAL PRIMARY KEY,
                date DATE NOT NULL,
                repo_name VARCHAR(100),
                total_commits INT DEFAULT 0,
                weighted_commits FLOAT DEFAULT 0,
                lines_added INT DEFAULT 0,
                lines_deleted INT DEFAULT 0,
                net_lines INT DEFAULT 0,
                productivity_score FLOAT DEFAULT 0,
                files_touched INT DEFAULT 0,
                day_type VARCHAR(50),
                day_type_icon VARCHAR(10),
                cognitive_load FLOAT DEFAULT 0,
                coding_hours FLOAT DEFAULT 0,
                testing_hours FLOAT DEFAULT 0,
                tags_breakdown JSONB DEFAULT '{{}}'::jsonb,
                UNIQUE(date, repo_name)
            )
        """).format(sql.Identifier(DB_SCHEMA)))

        # Table: Weekly Aggregations
        cur.execute(sql.SQL("""
            CREATE TABLE IF NOT EXISTS {}.weekly_stats (
                id SERIAL PRIMARY KEY,
                year INT NOT NULL,
                week INT NOT NULL,
                start_date DATE,
                end_date DATE,
                repo_name VARCHAR(100),
                productivity_score FLOAT DEFAULT 0,
                velocity_score FLOAT DEFAULT 0,
                metrics JSONB DEFAULT '{{}}'::jsonb,
                UNIQUE(year, week, repo_name)
            )
        """).format(sql.Identifier(DB_SCHEMA)))
        
        # Table: Mission Stats (from MISSION_REGISTRY.json)
        cur.execute(sql.SQL("""
            CREATE TABLE IF NOT EXISTS {}.mission_stats (
                mission_id VARCHAR(10) PRIMARY KEY,
                title TEXT,
                date_opened DATE,
                date_closed DATE,
                status VARCHAR(20),
                mission_type VARCHAR(30),
                organs JSONB DEFAULT '[]'::jsonb,
                repos JSONB DEFAULT '[]'::jsonb,
                cross_organ BOOLEAN DEFAULT FALSE,
                files_modified JSONB DEFAULT '[]'::jsonb,
                files_count INT DEFAULT 0,
                files_created INT DEFAULT 0,
                doc_sync_executed BOOLEAN DEFAULT FALSE,
                doc_verified BOOLEAN DEFAULT FALSE,
                duration_days INT DEFAULT 1,
                type_weight FLOAT DEFAULT 1.0,
                ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """).format(sql.Identifier(DB_SCHEMA)))

        # Add mission-aware columns to daily_stats (if not exist)
        for col_def in [
            ("mission_ids", "JSONB DEFAULT '[]'::jsonb"),
            ("mission_types", "JSONB DEFAULT '[]'::jsonb"),
            ("mission_count", "INT DEFAULT 0"),
            ("doc_sync_count", "INT DEFAULT 0"),
            ("cross_organ", "BOOLEAN DEFAULT FALSE"),
        ]:
            try:
                cur.execute(sql.SQL(
                    "ALTER TABLE {}.daily_stats ADD COLUMN IF NOT EXISTS {} " + col_def[1]
                ).format(sql.Identifier(DB_SCHEMA), sql.Identifier(col_def[0])))
            except Exception:
                pass  # Column already exists

        # Add mission-aware columns to weekly_stats (if not exist)
        for col_def in [
            ("mission_count", "INT DEFAULT 0"),
            ("mission_types", "JSONB DEFAULT '[]'::jsonb"),
            ("doc_sync_rate", "FLOAT DEFAULT 0"),
        ]:
            try:
                cur.execute(sql.SQL(
                    "ALTER TABLE {}.weekly_stats ADD COLUMN IF NOT EXISTS {} " + col_def[1]
                ).format(sql.Identifier(DB_SCHEMA), sql.Identifier(col_def[0])))
            except Exception:
                pass

        print("✅ Database initialization complete.")
        print(f"   - Schema: {DB_SCHEMA}")
        print("   - Tables: commits, daily_stats, weekly_stats, mission_stats")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        exit(1)

if __name__ == "__main__":
    init_db()
