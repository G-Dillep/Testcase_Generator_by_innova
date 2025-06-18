import os
import psycopg2

def delete_all_postgres_data():
    try:
        conn = psycopg2.connect(
            dbname=os.environ.get('POSTGRES_DB', 'my_postgres_db_dev'),
            user=os.environ.get('POSTGRES_USER', 'postgres'),
            password=os.environ.get('POSTGRES_PASSWORD', ''),
            host=os.environ.get('POSTGRES_HOST', 'localhost'),
            port=os.environ.get('POSTGRES_PORT', '5432')
        )
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE test_cases RESTART IDENTITY CASCADE;")
            print("✅ All data deleted from test_cases.")
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"❌ Error deleting data: {e}")

if __name__ == "__main__":
    delete_all_postgres_data() 