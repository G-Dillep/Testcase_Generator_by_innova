import os
import sys

# Add the Backend directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, "../.."))
sys.path.insert(0, backend_dir)

import lancedb
from app.config import Config
from app.models.create_dbs import create_LanceDB

def truncate_lance_db():
    """
    Truncates (deletes all records from) the LanceDB table and recreates it with the same schema.
    """
    try:
        print("🗑️ Starting LanceDB truncation process...")
        
        # Connect to LanceDB
        db = lancedb.connect(Config.LANCE_DB_PATH)
        
        # Drop the existing table
        try:
            db.drop_table(Config.TABLE_NAME_LANCE)
            print(f"✅ Successfully dropped table: {Config.TABLE_NAME_LANCE}")
        except Exception as e:
            print(f"⚠️ Table drop failed (might not exist): {e}")
        
        # Create new table with updated schema
        create_LanceDB()
        print("✅ Successfully recreated table with updated schema")
        
    except Exception as e:
        print(f"❌ Error during LanceDB truncation: {e}")
        raise

if __name__ == "__main__":
    truncate_lance_db() 