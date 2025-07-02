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
    ("project_id", pa.string()),
    ("vector", pa.list_(pa.float32(), 768)),
    ("storyID", pa.string()),
    ("storyDescription", pa.string()),
    ("test_case_content", pa.string()),
    ("filename", pa.string()),
    ("original_path", pa.string()),
    ("doc_content_text", pa.string()),
    ("embedding_timestamp", pa.timestamp("us")),
    ("source", pa.string())
])

def create_LanceDB():
    table = db.create_table(TABLE_NAME, schema=schema, exist_ok=True)
    print(f"✅ Table '{TABLE_NAME}' is ready.")
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
            print(f"✅ Database '{Config.POSTGRES_DB}' created successfully.")
        
        cursor.close()
        conn.close()

        # Now connect to our database and create tables
        conn = Config.get_postgres_connection()
        cursor = conn.cursor()
        
        # Enable uuid-ossp extension
        cursor.execute("""
            CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
        """)
        print("✅ Extension 'uuid-ossp' is ready.")
        
        # Create test_cases table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_cases (
                project_id TEXT,
                run_id UUID PRIMARY KEY,
                story_id TEXT NOT NULL,
                story_description TEXT,
                created_on TIMESTAMP WITHOUT TIME ZONE,
                test_case_json JSONB,
                total_test_cases INTEGER,
                total_impacted_test_cases INTEGER DEFAULT 0,
                impacted_test_cases_count INTEGER DEFAULT 0,
                last_impact_update_time TIMESTAMP WITHOUT TIME ZONE,
                test_case_generated BOOLEAN,
                impacted_test_case_generated BOOLEAN DEFAULT FALSE,
                source TEXT DEFAULT 'backend',
                inputs JSONB,
                has_impacts BOOLEAN DEFAULT FALSE,
                latest_impact_id UUID,
                CONSTRAINT unique_story_id UNIQUE(story_id)  -- Make story_id unique
            );
            
            -- Add index on story_id for faster joins
            CREATE INDEX IF NOT EXISTS idx_test_cases_story_id 
            ON test_cases(story_id);

            -- Add index for impacted test cases queries
            CREATE INDEX IF NOT EXISTS idx_test_cases_impacted 
            ON test_cases(impacted_test_case_generated)
            WHERE impacted_test_case_generated = TRUE;

            -- Add index for source field
            CREATE INDEX IF NOT EXISTS idx_test_cases_source
            ON test_cases(source);
        """)
        print("✅ Table 'test_cases' is ready.")

        # Create test_case_impacts table with enhanced referential integrity
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_case_impacts (
                impact_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                project_id TEXT NOT NULL,
                new_story_id TEXT NOT NULL,
                original_story_id TEXT NOT NULL,
                original_test_case_id TEXT NOT NULL,
                modified_test_case_id TEXT NOT NULL,
                original_run_id UUID NOT NULL,
                impact_created_on TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                source TEXT DEFAULT 'backend',
                similarity_score FLOAT,
                impact_analysis_json JSONB NOT NULL,
                previous_impact_id UUID,
                impact_version INT DEFAULT 1,
                impact_status TEXT DEFAULT 'active' CHECK (impact_status IN ('active', 'inactive')),
                impact_type TEXT NOT NULL CHECK (impact_type IN ('modification', 'deletion', 'addition')),
                impact_severity TEXT NOT NULL CHECK (impact_severity IN ('high', 'medium', 'low')),
                impact_priority INTEGER CHECK (impact_priority BETWEEN 1 AND 5),
                impact_details JSONB,
                CONSTRAINT fk_original_story 
                    FOREIGN KEY(original_story_id) 
                    REFERENCES test_cases(story_id)
                    ON DELETE CASCADE,
                CONSTRAINT fk_original_run
                    FOREIGN KEY(original_run_id)
                    REFERENCES test_cases(run_id)
                    ON DELETE CASCADE,
                CONSTRAINT fk_previous_impact
                    FOREIGN KEY(previous_impact_id)
                    REFERENCES test_case_impacts(impact_id)
                    ON DELETE SET NULL
            );

            -- Indexes for faster lookups
            CREATE INDEX IF NOT EXISTS idx_test_case_impacts_original_story 
            ON test_case_impacts(original_story_id);
            
            CREATE INDEX IF NOT EXISTS idx_test_case_impacts_new_story 
            ON test_case_impacts(new_story_id);
            
            CREATE INDEX IF NOT EXISTS idx_test_case_impacts_project 
            ON test_case_impacts(project_id);

            CREATE INDEX IF NOT EXISTS idx_test_case_impacts_chain
            ON test_case_impacts(previous_impact_id);

            CREATE INDEX IF NOT EXISTS idx_test_case_impacts_status
            ON test_case_impacts(impact_status);
        """)
        print("✅ Table 'test_case_impacts' is ready.")

        # Create impact_history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS impact_history (
                history_id UUID PRIMARY KEY,
                impact_id UUID NOT NULL,
                change_timestamp TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                changed_by TEXT,
                previous_status TEXT,
                new_status TEXT,
                change_reason TEXT,
                CONSTRAINT fk_impact
                    FOREIGN KEY(impact_id) 
                    REFERENCES test_case_impacts(impact_id)
                    ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_impact_history_impact_id 
            ON impact_history(impact_id);

            CREATE INDEX IF NOT EXISTS idx_impact_history_timestamp 
            ON impact_history(change_timestamp);
        """)
        print("✅ Table 'impact_history' is ready.")

        # Create view for impact metrics
        cursor.execute("""
            CREATE OR REPLACE VIEW impact_metrics AS
            WITH active_impacts AS (
                SELECT 
                    original_story_id,
                    COUNT(DISTINCT modified_test_case_id) as unique_impacted_test_cases,
                    COUNT(*) as total_impacts,
                    MAX(impact_created_on) as last_impact_date,
                    jsonb_agg(DISTINCT impact_type) as impact_types,
                    MAX(impact_priority) as highest_priority,
                    COUNT(CASE WHEN impact_severity = 'high' THEN 1 END) as high_severity_count,
                    COUNT(CASE WHEN impact_severity = 'medium' THEN 1 END) as medium_severity_count,
                    COUNT(CASE WHEN impact_severity = 'low' THEN 1 END) as low_severity_count
                FROM test_case_impacts
                WHERE impact_status = 'active'
                GROUP BY original_story_id
            )
            SELECT 
                tc.story_id,
                tc.project_id,
                tc.story_description,
                tc.total_test_cases,
                COALESCE(ai.unique_impacted_test_cases, 0) as impacted_test_cases,
                COALESCE(ai.total_impacts, 0) as total_impacts,
                ai.last_impact_date,
                ai.impact_types,
                ai.highest_priority,
                ai.high_severity_count,
                ai.medium_severity_count,
                ai.low_severity_count,
                CASE 
                    WHEN ai.unique_impacted_test_cases IS NULL THEN 0
                    ELSE ROUND(CAST((ai.unique_impacted_test_cases::float / tc.total_test_cases) * 100 AS numeric), 2)
                END as impact_percentage
            FROM test_cases tc
            LEFT JOIN active_impacts ai ON tc.story_id = ai.original_story_id;
        """)
        print("✅ View 'impact_metrics' is ready.")

        # Create view for test case impact summary (keeping the existing one)
        cursor.execute("""
        CREATE OR REPLACE VIEW test_case_impact_summary AS
        WITH impact_counts AS (
            SELECT 
                project_id,
                original_story_id as story_id,
                COUNT(*) as impacted_by_count
            FROM test_case_impacts
            WHERE impact_status = 'active'
            GROUP BY project_id, original_story_id
            
            UNION ALL
            
            SELECT 
                project_id,
                new_story_id as story_id,
                COUNT(*) as impacts_caused_count
            FROM test_case_impacts
            WHERE impact_status = 'active'
            GROUP BY project_id, new_story_id
        ),
        combined_counts AS (
            SELECT 
                project_id,
                story_id,
                SUM(impacted_by_count) as total_impacts
            FROM impact_counts
            GROUP BY project_id, story_id
        )
        SELECT 
            cc.project_id,
            cc.story_id,
            tc.story_description,
            tc.test_case_json,
            tc.created_on as test_case_generated_on,
            cc.total_impacts,
            EXISTS (
                SELECT 1 
                FROM test_case_impacts tci 
                WHERE tci.new_story_id = cc.story_id
                AND tci.impact_status = 'active'
            ) as has_caused_impacts,
            EXISTS (
                SELECT 1 
                FROM test_case_impacts tci 
                WHERE tci.original_story_id = cc.story_id
                AND tci.impact_status = 'active'
            ) as has_received_impacts
        FROM combined_counts cc
        JOIN test_cases tc ON tc.story_id = cc.story_id
        ORDER BY cc.total_impacts DESC;
        """)
        print("✅ View 'test_case_impact_summary' is ready.")
            
        conn.commit()
        print("\n✅ All database structures have been created/updated successfully!")
        
    except Exception as e:
        print(f"❌ Error creating/updating database structures: {e}")
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
        raise
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("\n🚀 Setting up database structures...")
    print("\n1️⃣ Creating LanceDB table...")
    create_LanceDB()

    print("\n2️⃣ Setting up PostgreSQL structures...")
    create_postgres_db()



 