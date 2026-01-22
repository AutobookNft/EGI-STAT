import os
import psycopg2
from psycopg2 import sql
import dotenv
from pathlib import Path

# Load config
dotenv.load_dotenv(Path(__file__).parent / '.env')

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_DATABASE")
DB_USER = os.getenv("DB_USERNAME")
DB_PASS = os.getenv("DB_PASSWORD")
DB_SCHEMA = os.getenv("DB_SCHEMA", "stat")

def reset_db():
    print(f"🗑️  Connecting to {DB_HOST} ({DB_NAME})...")
    
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
        
        print(f"⚠️  TRUNCATING tables in schema '{DB_SCHEMA}'...")
        
        # Truncate tables
        cur.execute(sql.SQL("TRUNCATE TABLE {}.commits, {}.weekly_stats, {}.daily_stats RESTART IDENTITY CASCADE").format(
                sql.Identifier(DB_SCHEMA),
                sql.Identifier(DB_SCHEMA),
                sql.Identifier(DB_SCHEMA)
            ))
            
        print("✅ Tables truncated successfully.")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error resetting database: {e}")
        exit(1)

if __name__ == "__main__":
    confirm = input("Are you sure you want to WIPE all data? (y/n): ")
    if confirm.lower() == 'y':
        reset_db()
    else:
        print("Aborted.")
