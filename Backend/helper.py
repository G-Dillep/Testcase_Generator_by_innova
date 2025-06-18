# Backend/print_lancedb.py

import lancedb
from app.config import Config

def print_lancedb_table():
    db = lancedb.connect(Config.LANCE_DB_PATH)
    table = db.open_table(Config.TABLE_NAME_LANCE)
    rows = table.to_pandas()
    print("All records in LanceDB:")
    print(rows)  # This prints the entire DataFrame

    # If you want to print just the story IDs:
    print("\nAll story IDs in LanceDB:")
    print(rows['storyID'].tolist())

if __name__ == "__main__":
    print_lancedb_table()