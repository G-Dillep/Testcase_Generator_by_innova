import os
import sys
import random
import json
import psycopg2
from psycopg2.extras import RealDictCursor

# Add the Backend directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, "../.."))
sys.path.insert(0, backend_dir)

from app.config import Config

def get_all_test_cases():
    """Fetch all test cases from the database that have exactly 50 test cases"""
    conn = Config.get_postgres_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT run_id, story_id, test_case_json, total_test_cases
                FROM test_cases
                WHERE test_case_json IS NOT NULL
                AND test_case_generated = TRUE
                AND total_test_cases = 50
            """)
            return cur.fetchall()
    finally:
        conn.close()

def trim_test_cases(test_case_json):
    """
    Randomly select between 40-50 test cases from the provided test case JSON,
    only if it has exactly 50 test cases
    """
    if isinstance(test_case_json, str):
        test_case_json = json.loads(test_case_json)
        
    if not test_case_json or 'test_cases' not in test_case_json:
        return test_case_json
        
    all_test_cases = test_case_json['test_cases']
    if not all_test_cases or len(all_test_cases) != 50:
        return test_case_json
        
    # Get random number between 40 and 50
    target_count = random.randint(40, 50)
    
    # Randomly select test cases while preserving order
    indices = sorted(random.sample(range(50), target_count))
    selected_test_cases = [all_test_cases[i] for i in indices]
    
    # Create new test case JSON with selected cases, preserving all other fields
    trimmed_json = test_case_json.copy()
    trimmed_json['test_cases'] = selected_test_cases
    
    return trimmed_json

def update_test_case(run_id, trimmed_json):
    """Update a test case in the database with trimmed test cases"""
    conn = Config.get_postgres_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE test_cases
                SET test_case_json = %s,
                    total_test_cases = %s
                WHERE run_id = %s
            """, (
                json.dumps(trimmed_json),
                len(trimmed_json.get('test_cases', [])),
                run_id
            ))
        conn.commit()
    finally:
        conn.close()

def main():
    print("🔍 Fetching test cases with exactly 50 test cases from database...")
    all_test_cases = get_all_test_cases()
    print(f"📊 Found {len(all_test_cases)} test cases with exactly 50 test cases")
    
    for idx, test_case in enumerate(all_test_cases, 1):
        run_id = test_case['run_id']
        story_id = test_case['story_id']
        original_count = test_case['total_test_cases']
        
        print(f"\n[{idx}/{len(all_test_cases)}] Processing story {story_id}")
        print(f"Original test case count: {original_count}")
        
        # Trim test cases
        trimmed_json = trim_test_cases(test_case['test_case_json'])
        new_count = len(trimmed_json.get('test_cases', []))
        
        if new_count != original_count:
            print(f"✂️  Trimming test cases from {original_count} to {new_count}")
            update_test_case(run_id, trimmed_json)
            print("✅ Updated in database")
        else:
            print("ℹ️  No trimming needed")

if __name__ == "__main__":
    main() 