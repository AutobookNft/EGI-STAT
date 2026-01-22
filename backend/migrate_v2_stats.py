import os
import psycopg2
from psycopg2 import sql
import dotenv

# Load config
dotenv.load_dotenv()

DB_HOST = os.getenv("DB_HOST", "db.bqdwexgodwwhckjgefph.supabase.co")
DB_PORT = os.getenv("DB_PORT", 5432)
DB_NAME = os.getenv("DB_DATABASE", "postgres")
DB_USER = os.getenv("DB_USERNAME", "postgres")
DB_PASS = os.getenv("DB_PASSWORD")
DB_SCHEMA = os.getenv("DB_SCHEMA", "stat")

def migrate_db():
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
        
        # Set search path
        cur.execute(sql.SQL("SET search_path TO {}, public").format(sql.Identifier(DB_SCHEMA)))
        
        print("🔨 Migrating daily_stats table...")
        
        # Add new columns individually to handle "IF NOT EXISTS" cleanly via exception catching or logic
        # Postgres 9.6+ supports IF NOT EXISTS in ADD COLUMN, assuming modern postgres
        
        columns = [
            ("files_touched", "INT DEFAULT 0"),
            ("day_type", "VARCHAR(50)"),
            ("day_type_icon", "VARCHAR(10)"),
            ("cognitive_load", "FLOAT DEFAULT 0"),
            ("coding_hours", "FLOAT DEFAULT 0"),
            ("testing_hours", "FLOAT DEFAULT 0")
        ]
        
        for col_name, col_def in columns:
            try:
                print(f"   Adding column {col_name}...")
                cur.execute(sql.SQL("""
                    ALTER TABLE daily_stats 
                    ADD COLUMN IF NOT EXISTS {} {}
                """).format(
                    sql.Identifier(col_name), 
                    sql.SQL(col_def)
                ))
            except Exception as e:
                print(f"   ⚠️ Warning adding {col_name}: {e}")

        print("✅ Migration complete.")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error migrating database: {e}")
        exit(1)

if __name__ == "__main__":
    migrate_db()
