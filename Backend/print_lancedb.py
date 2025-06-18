import lancedb

LANCE_DB_PATH = "E:/Srini Kosam/Test-Case-Generator/data/lance_db"  # Update if needed
TABLE_NAME = "user_stories"  # Update if needed

def print_lancedb_ids():
    db = lancedb.connect(LANCE_DB_PATH)
    table = db.open_table(TABLE_NAME)
    rows = table.to_pandas()
    print("All story IDs in LanceDB:")
    for story_id in rows['storyID']:
        print(story_id)

if __name__ == "__main__":
    print_lancedb_ids() 