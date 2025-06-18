import os
import sys

# Add the Backend directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, "../.."))
sys.path.insert(0, backend_dir)

import pyarrow as pa
import lancedb
import psycopg2
from app.config import Config

db = lancedb.connect(Config.LANCE_DB_PATH)
TABLE_NAME = Config.TABLE_NAME_LANCE
schema = pa.schema([
    ("vector", pa.list_(pa.float32(), 768)),
    ("storyID", pa.string()),
    ("storyDescription", pa.string()),
    ("test_case_content", pa.string()),
    ("filename", pa.string()),
    ("original_path", pa.string()),
    ("doc_content_text", pa.string()),
    ("embedding_timestamp", pa.timestamp("us"))
])

def create_LanceDB():
    table = db.create_table(TABLE_NAME, schema=schema, exist_ok=True)
    print(f"Table '{TABLE_NAME}' is ready.")
    return table

def create_postgres_db():
    try:
        # First try to connect to default postgres database to create our database if it doesn't exist
        conn = psycopg2.connect(
            dbname="postgres",
            user=Config.POSTGRES_USER,
            password=Config.POSTGRES_PASSWORD,
            host=Config.POSTGRES_HOST,
            port=Config.POSTGRES_PORT
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Check if our database exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (Config.POSTGRES_DB,))
        exists = cursor.fetchone()
        
        if not exists:
            cursor.execute(f"CREATE DATABASE {Config.POSTGRES_DB}")
            print(f"Database '{Config.POSTGRES_DB}' created successfully.")
        
        cursor.close()
        conn.close()

        # Now connect to our database and create the table if it doesn't exist
        conn = Config.get_postgres_connection()
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'test_cases'
            );
        """)
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            cursor.execute("""
                CREATE TABLE test_cases (
                    run_id UUID PRIMARY KEY,
                    story_id TEXT,
                    story_description TEXT,
                    created_on TIMESTAMP WITHOUT TIME ZONE,
                    test_case_json JSONB,
                    total_test_cases INTEGER,
                    test_case_generated BOOLEAN
                );
            """)
            print("Table 'test_cases' created successfully.")
        else:
            print("Table 'test_cases' already exists.")
            
        conn.commit()
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error creating database/table: {e}")
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("Creating LanceDB table...")
    create_LanceDB()



 