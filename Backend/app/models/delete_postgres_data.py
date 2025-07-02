import os
import sys

# Add the Backend directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, "../.."))
sys.path.insert(0, backend_dir)

import psycopg2
import lancedb
import shutil
from app.config import Config

def delete_all_postgres_data():
    """Delete all data from PostgreSQL tables"""
    try:
        conn = psycopg2.connect(
            dbname=Config.POSTGRES_DB,
            user=Config.POSTGRES_USER,
            password=Config.POSTGRES_PASSWORD,
            host=Config.POSTGRES_HOST,
            port=Config.POSTGRES_PORT
        )
        with conn.cursor() as cur:
            # Disable foreign key checks temporarily
            cur.execute("SET session_replication_role = 'replica';")
            
            # Truncate all tables
            cur.execute("""
                TRUNCATE TABLE test_cases, test_case_impacts, impact_history
                RESTART IDENTITY CASCADE;
            """)
            
            # Re-enable foreign key checks
            cur.execute("SET session_replication_role = 'origin';")
            
            print("✅ All data deleted from PostgreSQL tables.")
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"❌ Error deleting PostgreSQL data: {e}")

def delete_all_lance_data():
    """Delete all data from LanceDB"""
    try:
        # Connect to LanceDB
        db = lancedb.connect(Config.LANCE_DB_PATH)
        
        try:
            # Drop the table if it exists
            table = db.open_table(Config.TABLE_NAME_LANCE)
            db.drop_table(Config.TABLE_NAME_LANCE)
            print(f"✅ Dropped LanceDB table: {Config.TABLE_NAME_LANCE}")
        except Exception as e:
            print(f"⚠️ Table might not exist or other error: {e}")
        
        # Delete the entire lance_db directory
        lance_db_dir = Config.LANCE_DB_PATH
        if os.path.exists(lance_db_dir):
            shutil.rmtree(lance_db_dir)
            print(f"✅ Deleted LanceDB directory: {lance_db_dir}")
            
    except Exception as e:
        print(f"❌ Error deleting LanceDB data: {e}")

def clear_all_data():
    """Clear all data from both databases"""
    print("🗑️ Starting database cleanup...")
    
    # Clear PostgreSQL
    print("\n📊 Clearing PostgreSQL data...")
    delete_all_postgres_data()
    
    # Clear LanceDB
    print("\n📊 Clearing LanceDB data...")
    delete_all_lance_data()
    
    print("\n✨ Database cleanup completed!")

if __name__ == "__main__":
    clear_all_data() 